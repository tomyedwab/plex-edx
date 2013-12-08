NAME = 'EdX'
PREFIX = '/video/edx'
ART = 'art-default.jpg'
ICON = 'icon-default.png'

YT_VIDEO_PAGE    = 'http://www.youtube.com/watch?v=%s'

def Start():
	Plugin.AddPrefixHandler(PREFIX, Courses, NAME, ICON, ART)
	Plugin.AddViewGroup('List', viewMode='List', mediaType='items')
	Plugin.AddViewGroup('InfoList', viewMode='InfoList', mediaType='items')

	ObjectContainer.art = R(ART)
	ObjectContainer.title1 = NAME
	ObjectContainer.view_group = 'List'
	DirectoryObject.thumb = R(ICON)

	# HTTP.CacheTime = CACHE_1HOUR
	HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:15.0) Gecko/20100101 Firefox/15.0.1'


def GetCookie(name):
    cookies = HTTP.CookiesForURL("https://courses.edx.org/")
    if not cookies:
        return None
    cookies = cookies.split("; ")
    for cookie in cookies:
        key, val = cookie.split("=")
        if key == name:
            return val
    return None


def Login():
    if not Prefs["email"] or not Prefs["password"]:
        return False

    logged_in = GetCookie("edxloggedin")
    Log.Debug("Logged in: %s" % logged_in)

    if logged_in == "true":
        return True

    req = HTTP.Request("https://courses.edx.org/login")
    req.load()

    CSRF_TOKEN = GetCookie("csrftoken")

    req = HTTP.Request("https://courses.edx.org/login_ajax",
            headers={
                "Referer": "https://courses.edx.org/login",
                "X-CSRFToken": CSRF_TOKEN
            },
            values={
                "email": Prefs["email"],
                "password": Prefs["password"]
            })
    req.load()

    logged_in = GetCookie("edxloggedin")
    Log.Debug("Login: %s (%s)", req.headers, logged_in)
    return logged_in == "true"


@route('%s/courses' % PREFIX)
def Courses():

    Log.Debug("### Courses!")

    if not Login():
        oc = MediaContainer(view_group='List',
            message="Invalid or unspecified login infomation. "
                "Please add up-to-date account information in "
                "your Preferences.")
        oc.Append(PrefsItem('Preferences'))
        return oc

    dashboard = HTML.ElementFromURL("https://courses.edx.org/dashboard")

    oc = ObjectContainer(title2='EdX Courses', view_group='List', http_cookies=HTTP.CookiesForURL('https://courses.edx.org/'))

    courses = dashboard.xpath("//li[@class='course-item']")
    for course in courses:
        entry = course.xpath(".//section[@class='info']//h3//a")[0]
        title = entry.text
        url = entry.attrib.get("href")[:-5]
        oc.add(DirectoryObject(key=Callback(CourseNav, title=title, url=url), title=title))

    oc.add(PrefsObject(title='Preferences'))

    return oc


def LoadCourseNav(url):
    if not Login():
        return None

    course_page = HTML.ElementFromURL("https://courses.edx.org/%s/courseware" % url)

    nav = []
    chapters = course_page.xpath("//nav//div[@class='chapter']")
    for chapter in chapters:
        title = chapter.xpath("h3")[0].attrib.get("aria-label")
        entries = chapter.xpath(".//ul//li//a")
        nav_entries = []
        for entry in entries:
            entry_url = entry.attrib.get("href")
            entry_title = entry.xpath(".//p")[0].text
            nav_entries.append({
                "url": entry_url,
                "title": entry_title
            })

        nav.append({
            "idx": len(nav),
            "title": title,
            "entries": nav_entries
        })

    return nav


@route('%s/course' % PREFIX)
def CourseNav(title, url):
    Log.Debug("### Course: %s %s" % (title, url))

    nav = LoadCourseNav(url)
    if not nav:
        return MessageContainer("Invalid email/password",
                "An invalid account email or password was specified. "
                "Please update your preferences with valid account information")

    oc = ObjectContainer(title2=title, view_group='List', http_cookies=HTTP.CookiesForURL('https://courses.edx.org/'))

    for chapter in nav:
        oc.add(DirectoryObject(key=Callback(ChapterNav, title=chapter["title"], url=url, idx=chapter["idx"]), title=chapter["title"]))
    return oc


@route('%s/chapter' % PREFIX)
def ChapterNav(title, url, idx):
    Log.Debug("### Chapter: %d %s %s" % (int(idx), title, url))

    nav = LoadCourseNav(url)
    if not nav:
        return MessageContainer("Invalid email/password",
                "An invalid account email or password was specified. "
                "Please update your preferences with valid account information")
    chapter = nav[int(idx)]

    oc = ObjectContainer(title2=title, http_cookies=HTTP.CookiesForURL('https://courses.edx.org/'))

    for entry in chapter["entries"]:
        oc.add(DirectoryObject(key=Callback(ContentNav, title=entry["title"], url=entry["url"]), title=entry["title"]))

    return oc


@route('%s/content' % PREFIX)
def ContentNav(title, url):
    Log.Debug("### Content: %s %s" % (title, url))

    content_page = HTML.ElementFromURL("https://courses.edx.org/%s" % url)

    oc = ObjectContainer(title2=title, http_cookies=HTTP.CookiesForURL('https://courses.edx.org/'))

    sequences = content_page.xpath("//section[@class='course-content']//div[contains(concat(' ',normalize-space(@class),' '),' seq_contents ')]")
    for seq_data in sequences:
        sequence_html = HTML.ElementFromString(seq_data.text)
        videos = sequence_html.xpath("//section//ol//li//section[@data-type='Video']")
        for video in videos:
            video_title = video.xpath(".//h2")[0].text or "(No title)"
            video_id = video.xpath(".//div")[0].attrib.get("data-streams").split(":")[1]
            Log.Debug("Video %s: %s" % (video_id, video_title))

            # TODO: Thumbnail, duration, etc.
            oc.add(VideoClipObject(
                url = YT_VIDEO_PAGE % video_id,
                title = video_title,
            ))

    return oc
