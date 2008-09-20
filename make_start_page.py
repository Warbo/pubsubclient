import lxml.etree as etree
from lxml.etree import ElementTree, Element, SubElement
import os

page_file = open("start.html", 'w')

page = Element('html')
head = SubElement(page, 'head')
css_link = SubElement(head, 'link', attrib={"rel":"stylesheet", "type":"text/css", "href":"page_settings/test1/item.css"})
body = SubElement(page, 'body')

wholediv = SubElement(body, 'div', attrib={'class':'whole'})
titlediv = SubElement(wholediv, 'div', attrib={"class":"title"})
maindiv = SubElement(wholediv, 'div', attrib={"class":"main"})
body_text = SubElement(maindiv, 'a')
title = SubElement(titlediv, 'a')

title.text = "Welcome to appname"

body_text.text = "If you need any help please consult the documentation or email one of the developers."

page_file.write(etree.tostring(page, pretty_print=True))
page_file.close()

