from requests_toolbelt.utils import dump
from colorama import Fore, Style, init
from loguru import logger
from sys import stdout
from time import sleep
from re import findall
from shutil import copyfileobj

import concurrent.futures
import requests
import argparse
import urllib3
import json
import os


request_headers = {
    "User-Agent": "INE/2.7.6 CFNetwork/1240.0.4 Darwin/20.5.0",
    "X-Ine-Mobile": "PMJtkRFFmQ90zc4bU1FHbT4zOMpFPQCFsCnt5m1To6MIKUDUZI6sQLdCKljBJ6Qk",
    "Accept-Language": "en-us",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "close"
}

proxy_config = {
    # "http": "127.0.0.1:8080",
    # "https": "127.0.0.1:8080",
}

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
init(autoreset=True)


def write_into_file(filename, method, data):
    with open(filename, method, encoding="utf-8") as f:
        f.write(data)


def write_into_binary_file(filename, data):
    with open(filename, "wb") as f:
        copyfileobj(data, f)


def read_config(config_file):
    with open(config_file, "r") as f:
        config = json.loads(f.read().strip())
        username = config.get("username")
        password = config.get("password")

        if username and password:
            return username, password

        else:
            logger.opt(colors=True).error(f"No credentials were entered in <cyan>{config_file}</cyan>")
            exit()


def read_all_courses_file(all_courses_file):
    with open(all_courses_file, "r", encoding="utf-8") as f:
        course_contents = json.loads(f.read().strip())
        return course_contents


def banner():
    banner_text = r"""{}
██╗███╗   ██╗███████╗    ██████╗ ██╗     
██║████╗  ██║██╔════╝    ██╔══██╗██║     
{}██║██╔██╗ ██║█████╗█████╗██║  ██║██║     
██║██║╚██╗██║██╔══╝╚════╝██║  ██║██║     
{}██║██║ ╚████║███████╗    ██████╔╝███████╗
╚═╝╚═╝  ╚═══╝╚══════╝    ╚═════╝ ╚══════╝
""".format(
        Fore.CYAN, Fore.YELLOW, Fore.BLUE
    )

    print(banner_text)


def debug_requests(request_object):
    try:
        logger.debug(dump.dump_all(request_object).decode("utf-8"))
    except:
        logger.error("Can't debug the request, possibly contains binary characters")


def login():
    login_url = "https://uaa.ine.com:443/uaa/mobile/authenticate"
    username, password = read_config("config.json")

    login_json_body = {
        "username": username,
        "password": password,
    }

    login_request = requests.post(
        login_url, headers=request_headers, json=login_json_body, proxies=proxy_config, verify=False
    )

    if login_request.status_code == 200:
        logger.opt(colors=True).success("Logged in!")
        login_response = json.loads(login_request.text)

        authorization_token = login_response["data"]["tokens"]["data"]["Bearer"]
        request_headers["Authorization"] = f"Bearer {authorization_token}"

    elif login_request.status_code == 401:
        login_response = json.loads(login_request.text)

        if login_response.get("error").get("code") == "username_or_password_invalid":
            logger.opt(colors=True).error("Wrong credentials specified!")
            exit()

    else:
        debug_requests(login_request)
        logger.opt(colors=True).error("There was an issue logging in!")


def refresh_token(original_request):
    logger.opt(colors=True).info("Fetching refresh token..")
    refresh_endpoint = "https://uaa.ine.com:443/uaa/auth/refresh-token"
    request_headers["Host"] = "uaa.ine.com"
    refresh_request = requests.post(refresh_endpoint, headers=request_headers, proxies=proxy_config, verify=False)
    request_headers.pop("Host")

    logger.opt(colors=True).debug("Original request:")
    debug_requests(original_request)
    print()

    logger.opt(colors=True).debug("Refresh token request:")
    debug_requests(refresh_request)
    print()

    if refresh_request.status_code == 200:
        logger.opt(colors=True).success("Got refresh token!")
        refresh_request_response = json.loads(refresh_request.text)

        authorization_token = refresh_request_response["data"]["tokens"]["data"]["Bearer"]
        request_headers["Authorization"] = f"Bearer {authorization_token}"
        return True

    else:
        logger.opt(colors=True).error("There was an issue refreshing the token, doing the login request instead!")
        login()
        return False


def addArguments():
    parser = argparse.ArgumentParser(
        usage=f"\r{Style.BRIGHT}{Fore.WHITE}Usage: {Fore.BLUE}python3 ine.py --all{Fore.RED}"
    )
    parser._optionals.title = "Help"

    basicFuncs = parser.add_argument_group(f"{Fore.CYAN}Basic arguments (one or more)")
    basicFuncs.add_argument(
        "-l",
        "--log-output",
        action="store",
        dest="log",
        default=False,
        help="Logs output of the script (if required later)",
    )
    basicFuncs.add_argument(
        "-lct",
        "--list-categories",
        action="store_true",
        dest="list_categories",
        default=False,
        help="List all categories",
    )
    basicFuncs.add_argument(
        "-lcc",
        "--list-courses",
        action="store_true",
        dest="list_courses",
        default=False,
        help="List all courses",
    )
    basicFuncs.add_argument(
        "-lcct",
        "--list-categories-courses",
        action="store",
        dest="lcct",
        default=False,
        help="List all courses of a specific category UUID from -lct",
    )

    opts = parser.add_argument_group(f"{Fore.YELLOW}Necessary arguments")
    opts.add_argument(
        "-p",
        "--processes",
        action="store",
        dest="processes",
        default=False,
        help="Number of parallel processes to launch (2 if nothing specified)",
    )
    opts.add_argument(
        "-c",
        "--course",
        action="store",
        dest="course",
        default=False,
        help="Download course based on provided UUID from -lcc",
    )
    opts.add_argument(
        "-ct",
        "--category",
        action="store",
        dest="category",
        default=False,
        help="Download whole category based on provided UUID from -lct",
    )
    opts.add_argument(
        "-a",
        "--all",
        action="store_true",
        dest="all",
        default=False,
        help=f"Download all courses of all categories{Style.RESET_ALL}",
    )

    args = parser.parse_args()
    return (args, parser)


def fetch_all_courses(to_write_to):
    if os.path.exists(to_write_to):
        logger.opt(colors=True).warning(f"{to_write_to} already exists, not fetching the course list again.")
        logger.opt(colors=True).warning(f"Delete this file if you want to fetch a fresh list!")

    else:
        all_courses_api_endpoint = (
            "https://content-api.rmotr.com/api/v1/courses?page_size=none&status=published&active=true"
        )
        logger.opt(colors=True).info("Fetching course contents, this might take some time!")
        course_data = requests.get(all_courses_api_endpoint,
            headers=request_headers,
            proxies=proxy_config,
            verify=False
        )

        if course_data.status_code == 200:
            logger.opt(colors=True).success(f"Got the course contents, placing them in {to_write_to}")
            json_data = json.loads(course_data.text)

            logger.opt(colors=True).info(f"Total number of courses: {len(json_data)}")
            all_courses = json.dumps(json_data, indent=4, default=str)

            with open(to_write_to, "w+", encoding="utf-8") as f:
                f.write(all_courses)

        elif course_data.status_code == 401 or course_data.status_code == 403 or course_data.status_code == 502:
            logger.warning("Sleeping for 10 seconds, server might be rate limiting!")
            sleep(10)
            refresh_token(course_data)

        else:
            logger.opt(colors=True).error("There was some issue in fetching all the courses' metadata")


def fetch_user_subscriptions(course_contents, outfile, all_courses_metadata):
    logger.opt(colors=True).info("Fetching the user paid subscriptions and access levels")
    courses_with_access = 0

    user_subs = requests.get(
        "https://subscriptions.ine.com/subscriptions/subscriptions",
        headers=request_headers,
        proxies=proxy_config,
        verify=False,
    )

    if user_subs.status_code == 200:
        user_paid_subs = {}
        all_courses = []
        subscriptions = json.loads(user_subs.text).get("data")[0].get("passes").get("data")

        for subs in subscriptions:
            pass_id = subs.get("content_pass_id")
            pass_name = subs.get("name")
            # print(pass_id, pass_name)
            user_paid_subs[pass_id] = pass_name

        with open(all_courses_metadata, "r", encoding="utf-8") as f:
            course_contents = json.loads(f.read().strip())

            for courses in course_contents:
                related_passes = courses.get("access").get("related_passes")

                for subscription_details in related_passes:
                    sub_id = subscription_details.get("id")

                    for paid_subs_id, paid_subs_name in user_paid_subs.items():
                        # print(paid_subs_name)

                        if paid_subs_id == sub_id:
                            courses_with_access += 1
                            all_courses.append(courses)
                            # print(paid_subs_name)

        unique_courses = {each["name"]: each for each in all_courses}.values()
        all_courses = list(unique_courses)

        logger.opt(colors=True).debug(f"Total number of courses accessible to our user: {courses_with_access}")
        logger.opt(colors=True).debug(f"Writing the courses with access to in {outfile}")

        with open(outfile, "w+", encoding="utf-8") as f:
            f.write(json.dumps(all_courses, indent=4, default=str))

        return all_courses

    elif user_subs.status_code == 401 or user_subs.status_code == 403 or user_subs.status_code == 502:
        logger.warning("Sleeping for 10 seconds, server might be rate limiting!")
        sleep(10)
        refresh_token(user_subs)

    else:
        logger.opt(colors=True).error("There was an issue fetching the user subscriptions")


def fetch_course_categories(course_contents):
    logger.opt(colors=True).info("Fetching course categories from the course files")
    course_categories = {}

    for courses in course_contents:
        all_categories = courses.get("learning_areas")

        for categories in all_categories:
            category_id = categories["id"]
            category_name = categories["name"]

            course_categories[category_id] = category_name

    for category_id, category_name in course_categories.items():
        pass
        logger.opt(colors=True).debug(f"{category_id} | {category_name}")


def fetch_specific_category_courses(course_contents, passed_category_id):
    logger.opt(colors=True).info(f"Fetching all courses from the category: '{passed_category_id}'")

    course_length = 0
    category_courses = []

    for courses in course_contents:
        all_categories = courses.get("learning_areas")

        for categories in all_categories:
            category_id = categories.get("id")

            if category_id == passed_category_id:
                course_length += 1
                category_courses.append(courses)
                logger.opt(colors=True).debug(f"{courses.get('id')} | {courses.get('name')}")

    logger.opt(colors=True).info(f"Total number of courses: {course_length}")
    return category_courses


def fetch_courses(course_contents):
    logger.opt(colors=True).info("Fetching courses from the course files")
    all_courses = {}
    course_length = 0

    for courses in course_contents:
        course_length += 1
        course_id = courses.get("id")
        course_name = courses.get("name")

        all_courses[course_id] = course_name

    for course_id, course_name in all_courses.items():
        pass
        logger.opt(colors=True).debug(f"{course_id} | {course_name}")

    logger.opt(colors=True).info(f"Total <green>number</green> of courses: {course_length}")


def download_aria2c(filename, url):
    command = f'aria2c -s 10 -j 10 -x 16 -c -o "{filename}" "{url}" -q'
    logger.opt(colors=True).debug(command)
    os.system(command)


def download_video(course_name, content_uuid, complete_path, index):
    logger.opt(colors=True).info(f"Fetching video and subs of '{content_uuid}' from '{course_name}'")

    video_metadata = requests.get(
        f"https://video.rmotr.com/api/v1/videos/{content_uuid}/media",
        headers=request_headers,
        proxies=proxy_config,
        verify=False,
    )

    if video_metadata.status_code == 200:
        vid_meta = json.loads(video_metadata.text)
        video_title = vid_meta.get("title").split("/")[::-1][0]

        if (".mp4" or ".mov") in video_title:
            video_name = f"{index} - {video_title}"
            subs_name = video_name.replace(".mp4", ".srt").replace(".mov", ".srt")

        else:
            video_name = f"{index} - {video_title}.mp4"
            subs_name = f"{video_name}.srt"

        video_contents = vid_meta.get("playlist")[0]
        video_tracks = video_contents.get("tracks")

        if not os.path.isfile(f"{complete_path}/{video_name}") or os.path.isfile(f"{complete_path}/{video_name}.aria2"):
            video_sources = video_contents.get("sources")

            file_sizes = []

            for video_details in video_sources[::-1]:
                video_size = video_details.get("filesize")

                if video_size:
                    file_sizes.append(video_size)

            for video_details in video_sources[::-1]:
                video_download_url = video_details.get("file")
                video_width = video_details.get("width")
                video_height = video_details.get("height")
                video_size = video_details.get("filesize")

                if sorted(file_sizes)[::-1][0] == video_size:
                    download_aria2c(f"{complete_path}/{video_name}", video_download_url)

        else:
            logger.opt(colors=True).warning(f"{complete_path}/{video_name} already exists!")

        # Check for subs
        if not os.path.isfile(f"{complete_path}/{subs_name}"):
            for video_subs in video_tracks:
                subs_label = video_subs.get("label")
                subs_language = video_subs.get("language")
                subs_download_url = video_subs.get("file")

                if subs_label and (subs_label == "English" or subs_language == "en"):
                    download_aria2c(f"{complete_path}/{subs_name}", subs_download_url)

        else:
            logger.opt(colors=True).warning(f"{complete_path}/{subs_name} already exists!")

    elif video_metadata.status_code == 401 or video_metadata.status_code == 403 or video_metadata.status_code == 502:
        logger.warning("Sleeping for 10 seconds, server might be rate limiting!")
        sleep(10)
        refresh_token(video_metadata)
        download_video(course_name, content_uuid, complete_path, index)

    else:
        logger.opt(colors=True).error(f"There was an issue fetching the video {content_uuid} from {course_name}")
        debug_requests(video_metadata)
        download_video(course_name, content_uuid, complete_path, index)


def download_quiz(course_name, content_uuid, complete_path, index):
    logger.opt(colors=True).info(f"Fetching quiz '{content_uuid}' from '{course_name}'")

    initial_quiz_attempt = requests.post(
        f"https://quiz.rmotr.com/api/v1/quizzes/{content_uuid}/attempts",
        headers=request_headers,
        proxies=proxy_config,
        verify=False,
    )

    if initial_quiz_attempt:
        quiz_meta = json.loads(initial_quiz_attempt.text)
        quiz_id = quiz_meta.get("id")

        questions = quiz_meta.get("questions").get("questions")
        quiz_meta["status"] = "finished"
        quiz_meta["questions"] = questions
        quiz_title = (
            quiz_meta.get("source")
            .get("metadata")
            .get("video_reference")
            .split("/")[::-1][0]
            .replace(".mp4", ".txt")
            .replace(".mov", ".txt")
        )
        quiz_file_name = f"{complete_path}/{index} - {quiz_title}"

        if not os.path.isfile(quiz_file_name.replace(".txt", "_quiz_notsolved.txt")):
            quiz_attempt = requests.put(
                f"https://quiz.rmotr.com/api/v1/quizzes/{content_uuid}/attempts/{quiz_id}",
                headers=request_headers,
                json=quiz_meta,
                proxies=proxy_config,
                verify=False,
            )

            if quiz_attempt.status_code == 200:
                to_write = ""
                quiz_response = json.loads(quiz_attempt.text)
                quiz_questions = quiz_response.get("questions").get("questions")

                for questions in quiz_questions:
                    question_content = questions.get("_content")
                    answers_list = questions.get("answers")

                    to_write += f"[&] {question_content}\n"

                    for answers in answers_list:
                        answers_content = answers.get("_content")
                        is_answer_correct = answers.get("is_correct")

                        if is_answer_correct:
                            to_write += f"- {answers_content} -- Correct\n"

                        else:
                            to_write += f"- {answers_content}\n"

                    to_write += "\n"

                logger.opt(colors=True).debug(f"Got the quiz, writing into '{quiz_file_name}'")

                # Without correct answer placed in the file
                write_into_file(
                    quiz_file_name.replace(".txt", "_quiz_notsolved.txt"),
                    "w+",
                    to_write.replace(" -- Correct", ""),
                )

                # With correct answer placed in the file
                write_into_file(quiz_file_name.replace(".txt", "_quiz_solved.txt"), "w+", to_write)

            elif quiz_attempt.status_code == 400:
                logger.opt(colors=True).warning(f"The quiz attempt with id {quiz_id} has already been made!")

            elif quiz_attempt.status_code == 401 or quiz_attempt.status_code == 403 or quiz_attempt.status_code == 502:
                logger.warning("Sleeping for 10 seconds, server might be rate limiting!")
                sleep(10)
                refresh_token(quiz_attempt)

            else:
                logger.opt(colors=True).error(f"There was an issue fetching the quiz {content_uuid} with id {quiz_id}")

        else:
            logger.opt(colors=True).warning(f"The quiz file '{quiz_file_name}' already exists!")

    elif (
        initial_quiz_attempt.status_code == 401
        or initial_quiz_attempt.status_code == 403
        or initial_quiz_attempt.status_code == 502
    ):
        logger.warning("Sleeping for 10 seconds, server might be rate limiting!")
        sleep(10)
        refresh_token(initial_quiz_attempt)
        download_quiz(course_name, content_uuid, complete_path, index)

    else:
        logger.opt(colors=True).error(f"There was an issue fetching the quiz {content_uuid} from {course_name}")
        debug_requests(initial_quiz_attempt)
        download_quiz(course_name, content_uuid, complete_path, index)


def download_exercise(course_name, content_uuid, complete_path, index):
    logger.opt(colors=True).info(f"Fetching exercise '{content_uuid}' from '{course_name}'")

    exercise_request = requests.get(
        f"https://exercise.rmotr.com/api/v1/exercises?page_size=none&ids={content_uuid}",
        headers=request_headers,
        proxies=proxy_config,
        verify=False,
    )

    if exercise_request.status_code == 200:
        exercise_data = json.loads(exercise_request.text)[0]
        slug = exercise_data.get("slug")
        programming_language = str(exercise_data.get("language"))

        filename = f"{complete_path}/{index} - {slug}_exercise_{programming_language}.html"
        description = exercise_data.get("description_html")

        logger.opt(colors=True).debug(f"Writing the exercise into '{filename}'")
        write_into_file(filename, "w+", description)

    elif (
        exercise_request.status_code == 401
        or exercise_request.status_code == 403
        or exercise_request.status_code == 502
    ):
        logger.warning("Sleeping for 10 seconds, server might be rate limiting!")
        sleep(10)
        refresh_token(exercise_request)
        download_exercise(course_name, content_uuid, complete_path, index)

    else:
        logger.opt(colors=True).error(f"There was an issue fetching the exercise {content_uuid} from {course_name}")
        debug_requests(exercise_request)
        download_exercise(course_name, content_uuid, complete_path, index)


def download_slide_files(slide_url, slide_files_path, els_cdn_cookies, content_uuid, count, extension):
    logger.opt(colors=True).info(f"Downloading {extension.upper()} files of {slide_url}")
    is_not_end = True

    while is_not_end:
        if extension == "png":
            slide_file_name = f"img{count}.{extension}"

        elif extension == "woff":
            slide_file_name = f"fnt{count}.{extension}"

        else:
            slide_file_name = f"slide{count}.{extension}"

        slide_file_path = f"{slide_files_path}{slide_file_name}"

        if not os.path.isfile(slide_file_path):
            if extension == "png" or extension == "woff":
                file_request_url = f"https://els-cdn.content-api.ine.com/{content_uuid}/data/{slide_file_name}"
                slide_response = requests.get(
                    file_request_url,
                    headers=request_headers,
                    stream=True,
                    cookies=els_cdn_cookies,
                    proxies=proxy_config,
                    verify=False,
                )

                if slide_response.status_code == 200:
                    # logger.opt(colors=True).debug(f"Writing '{slide_file_name}' to '{slide_file_path}'")
                    write_into_binary_file(slide_file_path, slide_response.raw)
                    count += 1

                else:
                    is_not_end = False

            else:
                file_request_url = f"https://els-cdn.content-api.ine.com/{content_uuid}/data/{slide_file_name}"
                slide_response = requests.get(
                    file_request_url,
                    headers=request_headers,
                    cookies=els_cdn_cookies,
                    proxies=proxy_config,
                    verify=False,
                )

                if slide_response.status_code == 200:
                    # logger.opt(colors=True).debug(f"Writing '{slide_file_name}' to '{slide_file_path}'")
                    write_into_file(slide_file_path, "w", slide_response.text)
                    count += 1

                else:
                    is_not_end = False

        else:
            count += 1


def download_slide(course_name, content_uuid, complete_path, index):
    logger.opt(colors=True).info(f"Fetching slide '{content_uuid}' from '{course_name}'")

    slides_request = requests.get(
        f"https://content-api.rmotr.com/api/v1/iframes/{content_uuid}/media",
        headers=request_headers,
        proxies=proxy_config,
        verify=False,
    )

    if slides_request.status_code == 200:
        els_cdn_cookies = slides_request.cookies.get_dict()
        slides_data = json.loads(slides_request.text)
        slide_name = slides_data.get("name")

        slide_files = slides_data.get("files")
        slide_url = slides_data.get("url")
        slide_path = f"{complete_path}/{index} - {slide_name}_slides"
        slide_files_path = f"{slide_path}/data/"

        if not os.path.exists(slide_path):
            logger.opt(colors=True).debug(f"Creating directories: '{slide_path}'")
            os.makedirs(slide_path)

        if not os.path.exists(slide_files_path):
            logger.opt(colors=True).debug(f"Creating slide directory: '{slide_name}/data/'")
            os.makedirs(slide_files_path)

        # Downloading slide files
        for files in slide_files:
            slides_files_request = requests.get(
                f"https://file.rmotr.com/api/v1/files/{files}/download",
                headers=request_headers,
                proxies=proxy_config,
                verify=False,
            )

            if slides_files_request.status_code == 200:
                files_data = json.loads(slides_files_request.text)
                file_name = files_data.get("filename")
                file_download_url = files_data.get("download_url")
                final_file_name = f"{slide_path}/{file_name}"

                if not os.path.isfile(final_file_name):
                    download_aria2c(f"{slide_path}/{file_name}", file_download_url)

                else:
                    logger.opt(colors=True).warning(f"{final_file_name} already exists!")

            elif (
                slides_files_request.status_code == 401
                or slides_files_request.status_code == 403
                or slides_files_request.status_code == 502
            ):
                logger.warning("Sleeping for 10 seconds, server might be rate limiting!")
                sleep(10)
                refresh_token(slides_files_request)

            else:
                logger.opt(colors=True).error(
                    f"There was an issue fetching the file {files} of slide {content_uuid} from {course_name}"
                )

        # Downloading slide's index and required js files
        logger.opt(colors=True).info(f"Downloading index.html file of from {slide_url}")
        slide_index = requests.get(
            slide_url,
            headers=request_headers,
            proxies=proxy_config,
            cookies=els_cdn_cookies,
            verify=False,
        )

        if slide_index.status_code == 200:
            slide_index_file = slide_index.text
            index_outfile = f"{slide_path}/index.html"
            write_into_file(index_outfile, "w+", slide_index_file)

            required_js_files = findall(r'\<script\ssrc\="(.*?)"\>', slide_index_file)
            slide_required_files_url = "/".join(slide_url.split("/")[:-1])

            for files in required_js_files:
                required_fnames = files.split("?")[0]
                required_files_dl_path = f"{slide_required_files_url}/{required_fnames}"

                dl_required_files = requests.get(
                    required_files_dl_path,
                    headers=request_headers,
                    proxies=proxy_config,
                    cookies=els_cdn_cookies,
                    verify=False,
                )

                if dl_required_files.status_code == 200:
                    required_files_content = dl_required_files.text
                    write_into_file(f"{slide_path}/{required_fnames}", "w+", required_files_content)
                    logger.opt(colors=True).success(f"Writing '{required_fnames}' to '{slide_path}'")

                else:
                    logger.opt(colors=True).error(
                        f"There was an issue fetching the file {required_fnames} - {required_files_dl_path} from"
                        f" {course_name}"
                    )

        elif slide_index.status_code == 401 or slide_index.status_code == 403 or slide_index.status_code == 502:
            logger.warning("Sleeping for 10 seconds, server might be rate limiting!")
            sleep(10)
            refresh_token(slide_index)
            download_slide(course_name, content_uuid, complete_path, index)

        else:
            logger.opt(colors=True).error(
                f"There was an issue fetching the index file from {slide_url} from {course_name}"
            )
            debug_requests(slide_index)

        # Downloading the slide files
        download_slide_files(slide_url, slide_files_path, els_cdn_cookies, content_uuid, count=1, extension="css")
        download_slide_files(slide_url, slide_files_path, els_cdn_cookies, content_uuid, count=1, extension="js")
        download_slide_files(slide_url, slide_files_path, els_cdn_cookies, content_uuid, count=0, extension="png")
        download_slide_files(slide_url, slide_files_path, els_cdn_cookies, content_uuid, count=0, extension="woff")

    elif slides_request.status_code == 401 or slides_request.status_code == 403 or slides_request.status_code == 502:
        logger.warning("Sleeping for 10 seconds, server might be rate limiting!")
        sleep(10)
        refresh_token(slides_request)
        download_slide(course_name, content_uuid, complete_path, index)

    else:
        logger.opt(colors=True).error(f"There was an issue fetching the slide {content_uuid} from {course_name}")
        debug_requests(slides_request)
        download_slide(course_name, content_uuid, complete_path, index)


def download_lab(course_name, content_uuid, complete_path, index):
    logger.opt(colors=True).info(f"Fetching lab '{content_uuid}' from '{course_name}'")

    lab_request = requests.get(
        f"https://content-api.rmotr.com/api/v1/labs/{content_uuid}",
        headers=request_headers,
        proxies=proxy_config,
        verify=False,
    )

    if lab_request.status_code == 200:
        lab_data = json.loads(lab_request.text)
        name = lab_data.get("name")
        html_description = lab_data.get("description_html")
        html_solution = lab_data.get("solutions_html")

        lab_path = f"{complete_path}/{index} - {name}"

        if not os.path.exists(lab_path):
            os.makedirs(lab_path)

        lab_file_html = f"{lab_path}.html"
        lab_file_json = f"{lab_path}.json"

        # Does the JSON lab file exist?
        if not os.path.isfile(lab_file_json):
            logger.opt(colors=True).debug(f"Writing the lab file into '{lab_file_json}'")
            write_into_file(lab_file_json, "w+", json.dumps(lab_data, indent=4, default=str))

        else:
            logger.opt(colors=True).warning(f"The lab file {lab_file_json} already exists!")

        # Does the HTML lab file exist?
        if not os.path.isfile(lab_file_html):
            logger.opt(colors=True).debug(f"Writing the lab file into '{lab_file_html}'")

            if html_description and html_solution:
                to_write_to_lab = f"{html_description}\n{html_solution}"

            else:
                to_write_to_lab = html_description

            write_into_file(lab_file_html, "w+", to_write_to_lab)

        else:
            logger.opt(colors=True).warning(f"The lab file {lab_file_html} already exists!")

    elif lab_request.status_code == 401 or lab_request.status_code == 403 or lab_request.status_code == 502:
        logger.warning("Sleeping for 10 seconds, server might be rate limiting!")
        sleep(10)
        refresh_token(lab_request)
        download_lab(course_name, content_uuid, complete_path, index)

    elif lab_request.status_code == 404:
        logger.opt(colors=True).error(f"The lab {content_uuid} of {course_name} doesn't exist! lmao..")
        debug_requests(lab_request)

    else:
        logger.opt(colors=True).error(f"There was an issue fetching the lab {content_uuid} from {course_name}")
        debug_requests(lab_request)
        download_lab(course_name, content_uuid, complete_path, index)


def download_course(course_dict):
    name = str(course_dict.get("name"))
    slug = str(course_dict.get("slug"))
    files_uuids = course_dict.get("files_uuids")
    course_details = course_dict.get("content")

    # if os.path.isfile(f"{name}/{slug}.json"):
    #     logger.opt(colors=True).warning(f"The course {name} has been downloaded already!")
    #     return

    for _, details in zip(range(0 + 1, len(course_details) + 1), course_details):
        parent_dir = f'{str(_).zfill(2)} - {details.get("name")}'
        child_details = details.get("content")

        for __, child in zip(range(0 + 1, len(child_details) + 1), child_details):
            child_dirs = child.get("name")
            child_content = child.get("content")

            complete_path = f"{name}/{parent_dir}/{str(__).zfill(2)} - {child_dirs}"
            if not os.path.exists(complete_path):
                logger.opt(colors=True).success(f"Creating directories: '{complete_path}'")
                os.makedirs(complete_path)

            for ___, data in zip(range(0 + 1, len(child_content) + 1), child_content):
                content_uuid = data.get("uuid")
                content_type = data.get("content_type")
                index = str(___).zfill(2)

                if content_type == "video":
                    download_video(name, content_uuid, complete_path, index)
                    print()

                if content_type == "quiz":
                    download_quiz(name, content_uuid, complete_path, index)
                    print()

                if content_type == "exercise":
                    download_exercise(name, content_uuid, complete_path, index)
                    print()

                if content_type == "iframe":
                    download_slide(name, content_uuid, complete_path, index)
                    print()

                if content_type == "lab":
                    download_lab(name, content_uuid, complete_path, index)
                    print()

    print()

    # Downloading course .zip/.pdf files
    if len(files_uuids) != 0:
        for files in files_uuids:
            logger.opt(colors=True).info(f"Starting download of course file: {files}")
            slides_files_request = requests.get(
                f"https://file.rmotr.com/api/v1/files/{files}/download",
                headers=request_headers,
                proxies=proxy_config,
                verify=False,
            )

            if slides_files_request.status_code == 200:
                files_data = json.loads(slides_files_request.text)
                file_name = files_data.get("filename")
                file_download_url = files_data.get("download_url")
                final_file_name = f"{name}/{file_name}"

                if not os.path.isfile(final_file_name):
                    download_aria2c(f"{name}/{file_name}", file_download_url)

                else:
                    logger.opt(colors=True).warning(f"{final_file_name} already exists!")

            elif (
                slides_files_request.status_code == 401
                or slides_files_request.status_code == 403
                or slides_files_request.status_code == 502
            ):
                logger.warning("Sleeping for 10 seconds, server might be rate limiting!")
                sleep(10)
                refresh_token(slides_files_request)

            else:
                logger.opt(colors=True).error(f"There was an issue fetching the file {files} of {name}")

    print()

    # Writing json of the course into it's directory for better debugging/user information later on
    logger.opt(colors=True).success(f"Completed downloading of {name}")
    write_into_file(f"{name}/{slug}.json", "w+", json.dumps(course_dict, indent=4, default=str))
    print()


def main():
    banner()
    args, parser = addArguments()

    logger.remove()
    logger.add(
        stdout,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level>\t| <level>{message}</level>",
    )

    if args.processes:
        PROCESSES = int(args.processes)

    else:
        PROCESSES = 2

    if args.log:
        logger.add(
            args.log,
            backtrace=True,
            diagnose=True,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level}\t| {message}",
        )

    if any(vars(args).values()):
        all_courses_metadata = "all_courses_metadata.json"
        courses_with_access = "all_courses_with_access.json"

        login()
        print()

        fetch_all_courses(all_courses_metadata)
        print()

        all_course_contents = read_all_courses_file(all_courses_metadata)
        user_subscriptions = fetch_user_subscriptions(all_course_contents, courses_with_access, all_courses_metadata)

        print()

        if args.all:
            fetch_course_categories(user_subscriptions)
            print()

            fetch_courses(user_subscriptions)
            print()

            # for course in user_subscriptions:
            #     download_course(course)

            with concurrent.futures.ProcessPoolExecutor(max_workers=PROCESSES) as executor:
                executor.map(download_course, user_subscriptions)

        elif args.list_categories:
            fetch_course_categories(user_subscriptions)

        elif args.list_courses:
            fetch_courses(user_subscriptions)

        elif args.lcct:
            fetch_specific_category_courses(user_subscriptions, str(args.lcct))

        elif args.course:
            for course_dl in user_subscriptions:
                if args.course == course_dl.get("id"):
                    download_course(course_dl)

        elif args.category:
            category_courses = fetch_specific_category_courses(user_subscriptions, args.category)
            print()

            # for course in category_courses:
            #     download_course(course)

            with concurrent.futures.ProcessPoolExecutor(max_workers=PROCESSES) as executor:
                executor.map(download_course, category_courses)

    else:
        parser.print_help()
        exit()


if __name__ == "__main__":
    with logger.catch():
        main()
