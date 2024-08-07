# INE-DL (INE course downloader)

[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://GitHub.com/Anon-Exploiter/ine-dl.js/graphs/commit-activity)
[![python](https://img.shields.io/badge/python-3.8-blue.svg)](https://www.python.org/downloads/)
![GitHub](https://img.shields.io/github/license/Anon-Exploiter/ine-dl)
![GitHub closed issues](https://img.shields.io/github/issues-closed/Anon-Exploiter/ine-dl)
[![Twitter](https://img.shields.io/twitter/url/https/twitter.com/cloudposse.svg?style=social&label=Follow%20%40syed_umar)](https://twitter.com/syed__umar)
[![LinkedIn][linkedin-shield]][linkedin-url]

[contributors-shield]: https://img.shields.io/github/contributors/Anon-Exploiter/ine-dl.svg?style=flat-square
[contributors-url]: https://github.com/Anon-Exploiter/ine-dl/graphs/contributors
[issues-shield]: https://img.shields.io/github/issues/Anon-Exploiter/ine-dl?style=flat-square
[issues-url]: https://github.com/Anon-Exploiter/ine-dl/issues
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=flat-square&logo=linkedin&colorB=555
[linkedin-url]: https://www.linkedin.com/in/syedumararfeen/

**Python script to download INE courses including labs, exercises, quizzes, slides, and, videos!**

<img src="https://user-images.githubusercontent.com/18597330/179950027-c5856feb-bec0-4d32-bae9-0998fbb715a8.png" />

### How does this script work? (if you want to understand the code)

The script was written based on the APIs of **iOS application** to prevent Google's Invisible captcha implementation hence you will see a header (`X-Ine-Mobile`) hard coded in the script with an static API key required for the IOS API calls to succeed (this is hard-coded in the iOS application binary and can easily be grepped). 

**Initialization:**
1. The script starts with loading the credentials (`username/email` and `password`) from `config.json` file
2. It then proceeds to login into the INE account and loading the `JWT` token into Authorization header to use in next API calls
3. The script then does an API call to download the metadata of all the INE courses present and write into `all_courses_metadata.json`
4. It then checks for the subscriptions the user account has and filters the courses fetched and creates another file named `all_courses_with_access.json` with the data

**Downloading of videos:**
1. Does an API call to fetch the `video name`, `url`, and checks if subtitle URL is present and downloads all those!
2. Also *filters based on the resolution* and goes from 1080, 720 -> low

**Downloading of slides** (format looks like the [following](https://user-images.githubusercontent.com/18597330/179960035-7a00d727-ebc0-4744-be50-356f53ad03af.png)):
1. An initial request returns the slide metadata containing a link to `index.html` file (with cookies in response headers)
2. We store the cookies and then download `browsersupport.js` and `player.js` files (static can be reused with other slides)
3. INE uses a mix of `css`, `js`, `woff`, and, `pngs` but all have incrementable file names (format differs for text and binary files)
4. Wrote a `while loop` until the incremented file returns 404 and then stops the downloading of category: `CSS/JS/WOFF/PNG`
5. It also downloads any attachments added with the slides.

**Downloading of quizzes** (with right answers):
1. This was quite a pickle, looked into the quiz solving API call, first request returns a `JSON` containing the whole quiz content
2. Second request is a `PUT` request with right/wrong answers from user, in response to this, the JSON body now contains a new key `is_correct` containing the right answer
3. Wrote logic for posting the JSON body taken from the initial request, modified it to required standards, the server doesn't need options to be selected either
4. The `PUT` request then returns the right answers, *two files are made with no answers and correct answers*.

**Downloading of exercises**:
1. This was quite simple, an API call returns the contents in both `Markdown` and `HTML` format
2. For ease of cross-platform usage, I've only stored the `HTML` content with `_exercise_` in file name.

**Downloading of labs**:
1. You lose an edge here, in most of the cases, the labs are stored on INE cloud. 
2. The script only stores the `HTML content` of it (if present)

### Features
- Resume capability for a course video
- Download subtitles for the videos (if present)
- Download all courses without any prompt (option: -a / --all)
- Downloading slides, labs, exercises, quizzes, and, videos
	
### Install aria2
	
	sudo apt install aria2

### Help menu 

```bash
┌──(umar_0x01@b0x)-[~/scripts/ine-dl]
└─$ python3 ine.py

██╗███╗   ██╗███████╗    ██████╗ ██╗     
██║████╗  ██║██╔════╝    ██╔══██╗██║     
██║██╔██╗ ██║█████╗█████╗██║  ██║██║     
██║██║╚██╗██║██╔══╝╚════╝██║  ██║██║     
██║██║ ╚████║███████╗    ██████╔╝███████╗
╚═╝╚═╝  ╚═══╝╚══════╝    ╚═════╝ ╚══════╝

Usage: python3 ine.py --all

Help:
  -h, --help            show this help message and exit

Basic arguments (one or more):
  -l LOG, --log-output LOG
                        Logs output of the script (if required later)
  -lct, --list-categories
                        List all categories
  -lcc, --list-courses  List all courses
  -lcct LCCT, --list-categories-courses LCCT
                        List all courses of a specific category UUID from -lct

Necessary arguments:
  -p PROCESSES, --processes PROCESSES
                        Number of parallel processes to launch (2 if nothing specified)
  -c COURSE, --course COURSE
                        Download course based on provided UUID from -lcc
  -ct CATEGORY, --category CATEGORY
                        Download whole category based on provided UUID from -lct
  -a, --all             Download all courses of all categories

```

### Arguments usage

***Running the Script (displays help menu with no args)***

	python ine-dl.py

***Listing all the courses***

	python ine-dl.py -lc

***Listing course categories***

	python ine-dl.py -lct 

***Listing all the courses of a specific category***

	python ine-dl.py -lcct {category_id}

***Logging the script's output into a log file***

	python ine-dl.py <general_args> -l logfile.log

***Downloading all the INE course (your subscription has access to, with/without parallel processing)***

	python ine-dl.py --all
    python ine-dl.py --all -p 2

***Downloading a single course***

	python ine-dl.py -c {course_id}

***Downloading all courses of specified category (with/without parallel processes)***

	python ine-dl.py -ct {category_id}
    python ine-dl.py -ct {category_id} -p 2

### Screenshots

<img src="https://user-images.githubusercontent.com/18597330/179950027-c5856feb-bec0-4d32-bae9-0998fbb715a8.png" />
<img src="https://user-images.githubusercontent.com/18597330/179954269-c4d4b09b-a023-429d-b6d8-2082423ce8ff.png" />
<img src="https://user-images.githubusercontent.com/18597330/179954376-31f59667-b64d-4ee4-8888-a05564a9128a.png" />
<img src="https://user-images.githubusercontent.com/18597330/179954527-c6709ede-6172-4b0e-a548-dab47d4233d6.png" />


### Credits

- Inspired as always by downloaders of [r0oth3x49](https://github.com/r0oth3x49)
- Some ideas were taken from [Jayapraveen's downloader](https://github.com/Jayapraveen/INE-courses-downloader). Though his script is nice, it has a lot of bugs, I spent almost 2 holidays fixing those and then thought of writing my own. 

### Note 
Please use the script w.r.t the usage guidelines of INE. Do not exhaust their backend servers. Do not dump and share the courses publicly. 

Please use this on your own risk, If your account is blocked by the usage of this script, I won't be responsible. 
