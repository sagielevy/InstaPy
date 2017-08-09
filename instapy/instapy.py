"""OS Modules environ method to get the setup vars from the Environment"""
import logging
from datetime import datetime
from os import environ
from random import randint
from time import sleep

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
# from selenium.webdriver.firefox.options import Options
# from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.chrome.options import Options

from .clarifai_util import check_image
from .comment_util import comment_image
from .like_util import check_link
from .like_util import get_links_for_tag
from .like_util import get_tags
from .like_util import like_image
from .login_util import login_user
from .print_log_writer import log_follower_num
from .unfollow_util import dump_follow_restriction
from .unfollow_util import follow_user
from .unfollow_util import load_follow_restriction
from .unfollow_util import unfollow


class InstaPy:
    """Class to be instantiated to use the script"""

    def __init__(self, username=None, password=None):
        # self.display = Display(visible=0, size=(800, 600))
        # self.display.start()
        self.browser = self._init_webdriver_browser()
        self.logger = self._create_logger('./logs/logFile.txt')
        self.logger.info('Session started - %s' % (datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

        if username is None:
            self.username = environ.get('INSTA_USER')
        else:
            self.username = username

        if password is None:
            self.password = environ.get('INSTA_PW')
        else:
            self.password = password

        self.do_comment = False
        self.comment_percentage = 0

        self.followed = 0
        self.follow_restrict = load_follow_restriction()
        self.follow_times = 1
        self.do_follow = False
        self.follow_percentage = 0
        self.dont_include = ()

        self.dont_like = ('sex', 'nsfw')
        self.ignore_if_contains = ()

        self.use_clarifai = False
        self.clarifai_secret = None
        self.clarifai_id = None
        self.clarifai_img_tags = []

        self.aborting = False

    def login(self, browser=None):
        """Used to login the user either with the username and password"""

        # Actual default is self.browser
        if browser is None:
            browser = self.browser

        if not login_user(browser, self.username, self.password):
            self.logger.info('Wrong login data!')

            self.aborting = True
        else:
            self.logger.info('Logged in successfully!')

        log_follower_num(browser, self.username)

        return self

    def set_do_comment(self, enabled=False, percentage=0):
        """Defines if images should be commented or not
    percentage=25 -> ~ every 4th picture will be commented"""
        if self.aborting:
            return self

        self.do_comment = enabled
        self.comment_percentage = percentage

        return self

    def set_comments(self, comments=None):
        """Changes the possible comments"""
        if self.aborting:
            return self

        if comments is None:
            comments = ()

        # Force immutability
        self.comments = tuple(comments)

        return self

    def set_do_follow(self, enabled=False, percentage=0, times=1):
        """Defines if the user of the liked image should be followed"""
        if self.aborting:
            return self

        self.follow_times = times
        self.do_follow = enabled
        self.follow_percentage = percentage

        return self

    def set_dont_like(self, tags=None):
        """Changes the possible restriction tags, if one of this
     words is in the description, the image won't be liked"""
        if self.aborting:
            return self

        if tags is None:
            tags = ()

        # Force immutability
        self.dont_like = tuple(tags)

        return self

    def set_ignore_if_contains(self, words=None):
        """ignores the don't likes if the description contains
    one of the given words"""
        if self.aborting:
            return self

        if words is None:
            words = ()

        # Force immutability
        self.ignore_if_contains = tuple(words)

        return self

    def set_dont_include(self, friends=None):
        """Defines which accounts should not be unfollowed"""
        if self.aborting:
            return self

        if friends is None:
            friends = ()

        # Force immutability
        self.dont_include = tuple(friends)

        return self

    def set_use_clarifai(self, enabled=False, secret=None, proj_id=None):
        """Defines if the clarifai img api should be used
    Which 'project' will be used (only 5000 calls per month)"""
        if self.aborting:
            return self

        self.use_clarifai = enabled

        if secret is None and self.clarifai_secret is None:
            self.clarifai_secret = environ.get('CLARIFAI_SECRET')
        elif secret is not None:
            self.clarifai_secret = secret

        if proj_id is None and self.clarifai_id is None:
            self.clarifai_id = environ.get('CLARIFAI_ID')
        elif proj_id is not None:
            self.clarifai_id = proj_id

        return self

    def clarifai_check_img_for(self, tags=None, comment=False, comments=None):
        """Defines the tags, the images should be checked for"""
        if self.aborting:
            return self

        if tags is None and not self.clarifai_img_tags:
            self.use_clarifai = False
        elif tags:
            self.clarifai_img_tags.append((tags, comment, comments))

        return self

    def like_by_tags(self, tags=None, amount=50):
        """Likes (default) 50 images per given tag"""
        try:
            if self.aborting:
                return self

            liked_img = 0
            already_liked = 0
            inap_img = 0
            commented = 0
            followed = 0

            if tags is None:
                tags = ()

            for index, tag in enumerate(tags):
                self.logger.info('Tag [%d/%d]' % (index + 1, len(tags)))
                self.logger.info('--> ' + tag)

                try:
                    links = get_links_for_tag(self.browser, tag, amount)
                except WebDriverException:
                    self.logger.info('Too few images, aborting')

                    self.aborting = True
                    return self

                for i, link in enumerate(links):
                    self.logger.info('[%d/%d]' % (i + 1, len(links)))
                    self.logger.info(link)

                    try:
                        inappropriate, user_name = \
                            check_link(self.browser, link, self.dont_like,
                                       self.ignore_if_contains, self.username, self.logger)

                        if not inappropriate:
                            liked = like_image(self.browser, self.logger)

                            if liked:
                                liked_img += 1
                                checked_img = True
                                temp_comments = []
                                commenting = True if randint(0, 100) <= self.comment_percentage \
                                    else False
                                following = True if randint(0, 100) <= self.follow_percentage \
                                    else False

                                if self.use_clarifai and (following or commenting):
                                    try:
                                        checked_img, temp_comments = \
                                            check_image(self.browser, self.clarifai_id,
                                                        self.clarifai_secret,
                                                        self.clarifai_img_tags,
                                                        self.logger)
                                    except Exception as err:
                                        self.logger.info('Image check error: ' + str(err))

                                if self.do_comment and user_name not in self.dont_include \
                                        and checked_img and commenting:
                                    commented += comment_image(self.browser,
                                                               temp_comments if temp_comments
                                                               else self.comments, self.logger)
                                else:
                                    self.logger.info('--> Not commented')
                                    sleep(1)

                                if self.do_follow and user_name not in self.dont_include \
                                        and checked_img and following \
                                        and self.follow_restrict.get(user_name, 0) < self.follow_times:
                                    followed += follow_user(self.browser, user_name, self.follow_restrict, self.logger)
                                else:
                                    self.logger.info('--> Not following')
                                    sleep(1)
                            else:
                                already_liked += 1
                        else:
                            self.logger.info('Image not liked: Inappropriate')
                            inap_img += 1
                    except WebDriverException as err:
                        self.logger.error('Invalid Page: ' + str(err))

                    self.logger.info("")

            self.logger.info('Liked: ' + str(liked_img))
            self.logger.info('Already Liked: ' + str(already_liked))
            self.logger.info('Inappropriate: ' + str(inap_img))
            self.logger.info('Commented: ' + str(commented))
            self.logger.info('Followed: ' + str(followed))

            self.followed += followed
        except Exception as e:
            # An exception has occurred. End safety and exit
            self.end()
            exit(1)

        return self

    def like_from_image(self, url, amount=50):
        """Gets the tags from an image and likes 50 images for each tag"""
        if self.aborting:
            return self

        try:
            tags = get_tags(self.browser, url)
            self.logger.info(tags)
            self.like_by_tags(tags, amount)
        except TypeError as err:
            self.logger.error('Sorry, an error occured: ' + str(err))

            self.aborting = True
            return self

        return self

    def unfollow_users(self, amount=10, unfollow_oldest=False):
        """Unfollows (default) 10 users from your following list"""
        try:
            removed = 0

            while amount > 0:
                try:
                    removed += unfollow(self.browser, self.username, amount,
                                        self.dont_include, self.logger, unfollow_oldest)
                    amount -= removed
                except TypeError as err:
                    self.logger.error('Sorry, an error occurred: ' + str(err))

                    self.aborting = True
                    return self

                # If 10 or more people have been unfollowed and there are more to unfollow
                if amount > 0 and removed >= 10:
                    # Reset removed
                    removed = 0

                    # Sleep for some minutes after removing 10 people
                    self.logger.info('Sleeping for 5 min')
                    sleep(300)
        except Exception as e:
            # An exception has occurred. End safety and exit
            self.end()
            exit(1)

        return self

    def end(self):
        """Closes the current session"""
        dump_follow_restriction(self.follow_restrict)
        self.browser.delete_all_cookies()
        self.browser.close()
        # self.display.stop()

        self.logger.info('\nSession ended - %s\n'
                         % (datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        self.logger.info('-' * 20 + '\n')

        with open('./logs/followed.txt', 'w') as followFile:
            followFile.write(str(self.followed))

    def _init_webdriver_browser(self):
        # binary = FirefoxBinary(r'C:\Program Files (x86)\Mozilla Firefox\firefox.exe')
        chrome_options = Options()
        chrome_options.add_argument('--dns-prefetch-disable')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--lang=en-US')
        chrome_options.add_experimental_option('prefs', {'intl.accept_languages': 'en-US'})
        browser = webdriver.Chrome('./assets/chromedriver', chrome_options=chrome_options)
        # browser = webdriver.Firefox(executable_path='./assets/geckodriver',
        #                             firefox_options=chrome_options, firefox_binary=binary)

        browser.implicitly_wait(25)

        # Maximize to avoid missing elements and such
        browser.maximize_window()

        return browser

    def _create_logger(self, log_filename):
        logger = logging.Logger(__name__)

        # set up logging to console
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # create error file handler and set level to error
        handler = logging.FileHandler(log_filename, "a", encoding=None, delay="true")
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger
