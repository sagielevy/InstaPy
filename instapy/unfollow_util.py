"""Module which handles the follow features like unfollowing and following"""
import json
from time import sleep

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

_follow_div_class = "_gs38e"
_person_list_div_class = "_npuc5"
_person_name_text_class = "_2nunc"
_following_link_div_class = "_t98z6"


def unfollow(browser, username, amount, dont_include, logger, unfollow_oldest):
    """unfollows the given amount of users or the maximum allowed per iteration - 10 users"""
    unfollowNum = 0

    browser.get('https://www.instagram.com/' + username)

    following_link_div = browser.find_elements_by_class_name(_following_link_div_class)
    sleep(1)
    num_of_tries = 0

    # Make sure the necessary element is loaded (try 10 times)
    while len(following_link_div) < 3 and num_of_tries < 10:
        following_link_div = browser.find_elements_by_class_name(_following_link_div_class)
        sleep(1)
        num_of_tries += 1

    # Failed to unfollow
    if len(following_link_div) < 3:
        return unfollowNum

    # following_link = following_link_div[2].find_element_by_tag_name('a')
    following_link = following_link_div[2]
    following_link.click()

    sleep(2)

    person_list_div = browser.find_element_by_class_name(_follow_div_class)
    person_list = person_list_div.find_elements_by_class_name(_person_list_div_class)

    follow_div = browser.find_element_by_class_name(_follow_div_class)

    temp_list = []
    actions = ActionChains(browser)
    actions.move_to_element(follow_div)
    actions.click()
    actions.send_keys()
    actions.perform()

    # If unfollow_oldest=True, unfollow the oldest followed users first (FIFO)
    # Else, unfollow the recent users that have been followed (LIFO)
    if unfollow_oldest:
        # Load ALL followed users first (or until list is so long 1 second
        # is not enough to reach the end to load more)
        actions.send_keys(Keys.END).perform()
        sleep(1)
        actions.send_keys(Keys.HOME).perform()
        sleep(1)
        temp_list = person_list_div.find_elements_by_class_name(_person_list_div_class)

        while len(person_list) < len(temp_list):
            actions.send_keys(Keys.END).perform()
            sleep(1)
            actions.send_keys(Keys.HOME).perform()
            sleep(1)
            person_list = temp_list
            temp_list = person_list_div.find_elements_by_class_name(_person_list_div_class)

        # Finally, extract the names of users from the list in reversed order (and buttons)
        follow_div = browser.find_element_by_class_name(_follow_div_class)
        person_list = reversed([x.find_element_by_class_name(_person_name_text_class).text for x in person_list])
        follow_buttons = reversed(follow_div.find_elements_by_tag_name('button'))
    else:
        # Make sure enough users are loaded (as required by amount). If len(temp_list) == len(person_list) nothing has been loaded - stop
        while len(person_list) < amount and len(temp_list) != len(person_list):
            actions.send_keys(Keys.END).perform()
            sleep(1)
            actions.send_keys(Keys.HOME).perform()
            sleep(1)
            temp_list = person_list
            person_list = person_list_div.find_elements_by_class_name(_person_list_div_class)

        # Finally, extract the names of users from the list (and buttons)
        follow_div = browser.find_element_by_class_name(_follow_div_class)
        person_list = [x.find_element_by_class_name(_person_name_text_class).text for x in person_list]
        follow_buttons = follow_div.find_elements_by_tag_name('button')

    for button, person in zip(follow_buttons, person_list):
        if person not in dont_include:
            unfollowNum += 1
            button.click()
            logger.info('--> Now unfollowing: ' + person)
            sleep(15)

            # Stop if reached amount or if reached a maximum of 10
            if unfollowNum >= amount or unfollowNum == 10:
                break

    # Refresh page, just in case. Seeing some wierd things, people are not being unfollowed even after click
    browser.get('https://www.instagram.com/' + username)

    return unfollowNum


def follow_user(browser, user_name, follow_restrict, logger):
    """Follows the user of the currently opened image"""
    follow_button = browser.find_element_by_xpath("//article/header/span/button")
    sleep(2)

    if follow_button.text == 'Follow':
        follow_button.click()
        logger.info('--> Now following: %s' % user_name)

        follow_restrict[user_name] = follow_restrict.get(user_name, 0) + 1
        sleep(3)
        return 1

    else:
        logger.info('--> Already following')
        sleep(1)
        return 0


def dump_follow_restriction(followRes):
    """Dumps the given dictionary to a file using the json format"""
    with open('./logs/followRestriction.json', 'w') as followResFile:
        json.dump(followRes, followResFile)


def load_follow_restriction():
    """Loads the saved """
    with open('./logs/followRestriction.json') as followResFile:
        return json.load(followResFile)
