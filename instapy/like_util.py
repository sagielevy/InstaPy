"""Module that handles the like features"""
from math import ceil
from time import sleep
from re import findall
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import WebDriverException

_load_more_class = "_1cr2e _epyes"


def get_links_for_tag(browser, tag, amount):
    """Fetches the number of links specified
    by amount and returns a list of links"""
    browser.get('https://www.instagram.com/explore/tags/'
                + (tag[1:] if tag[:1] == '#' else tag))

    sleep(2)

    # clicking load more till there are 1000 posts
    body_elem = browser.find_element_by_tag_name('body')

    sleep(2)

    load_button = body_elem.find_element_by_xpath \
        ('//a[contains(@class, "{0}")]'.format(_load_more_class))
    body_elem.send_keys(Keys.END)
    sleep(2)

    load_button.click()

    body_elem.send_keys(Keys.HOME)
    sleep(1)

    main_elem = browser.find_element_by_tag_name('main')

    new_needed = int(ceil((amount - 33) / 12))

    for _ in range(new_needed):  # add images x * 12
        body_elem.send_keys(Keys.END)
        sleep(1)
        body_elem.send_keys(Keys.HOME)
        sleep(1)

    link_elems = main_elem.find_elements_by_tag_name('a')
    links = [link_elem.get_attribute('href') for link_elem in link_elems]

    return links[:amount]


def check_link(browser, link, dont_like, ignore_if_contains, username, logger):
    try:
        browser.get(link)
        sleep(2)

        """Check if the Post is Valid/Exists"""
        post_page = browser.execute_script("return window._sharedData.entry_data.PostPage")

        if post_page is None:
            logger.info('Unavailable Page: ' + link)
            return False, 'Unavailable Page'

        """Gets the description of the link and checks for the dont_like tags"""
        user_name = browser.execute_script(
            "return window._sharedData.entry_data.PostPage[0].graphql.shortcode_media.owner.username")

        image_text = None

        try:
            image_text = browser.execute_script(
                "return window._sharedData.entry_data.PostPage[0].graphql.shortcode_media.edge_media_to_caption.edges[0].node.text")
        except WebDriverException:
            pass

        """If the image has no description gets the first comment"""
        if image_text is None:
            try:
                image_text = browser.execute_script(
                    "return window._sharedData.entry_data.PostPage[0].graphql.shortcode_media.edge_media_to_comment.edges[0].node.text")
            except WebDriverException:
                pass

        if image_text is None:
            image_text = "No description"

        logger.info('Image from: ' + user_name)
        logger.info('Link: ' + link)
        logger.info('Description: ' + "".join([chr(s) for s in image_text.encode('ascii', 'ignore')]))

        text_words = image_text.split()

        for word in ignore_if_contains:
            if word in text_words:
                return False, user_name

        for tag in dont_like:
            if tag in text_words or user_name == username:
                return True, user_name

        return False, user_name
    except WebDriverException as e:
        logger.info(e)
        return True, None


def like_image(browser, logger):
    """Likes the browser opened image"""
    like_elem = browser.find_elements_by_xpath("//a[@role = 'button']/span[text()='Like']")
    liked_elem = browser.find_elements_by_xpath("//a[@role = 'button']/span[text()='Unlike']")

    if len(like_elem) == 1:
        browser.execute_script(
            "document.getElementsByClassName('" + like_elem[0].get_attribute("class") + "')[0].click()")
        logger.info('--> Image Liked!')
        sleep(2)
        return True
    elif len(liked_elem) == 1:
        logger.info('--> Already Liked!')
        return False
    else:
        logger.info('--> Invalid Like Element!')
        return False


def get_tags(browser, url):
    """Gets all the tags of the given description in the url"""
    browser.get(url)
    sleep(1)

    tags = None

    try:
        image_text = browser.execute_script(
            "return window._sharedData.entry_data.PostPage[0].graphql.shortcode_media.edge_media_to_caption.edges[0].node.text")

        if image_text is not None:
            tags = findall(r'#\w*', image_text)
    except WebDriverException:
        pass

    return tags
