from __future__ import print_function
from flask import Flask, render_template, request, redirect, url_for

import json
import pygraphviz as pgv
import re
from lxml import etree
import StringIO
import urllib
import urllib2
import string
import sys
import os
import os.path

app = Flask(__name__)

os.environ['PATH'] = os.environ['PATH'] + ':/usr/local/bin'
os.environ['GV_FILE_PATH'] = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static/images/')) + '/'

print('PATH: ' + os.environ['PATH'], file=sys.stderr)
print('GV_FILE_PATH: ' + os.environ['GV_FILE_PATH'], file=sys.stderr)

def get_people():
    filepath = os.path.abspath(os.path.join(os.path.dirname(__file__), 'people.json'))
    return get_file_contents(filepath)

def get_file_contents(filename):
    data = None

    try:
        fp = open(filename, 'rb')
        try:
            contents = fp.read()
            data = json.loads(contents)
        finally:
            fp.close()
    except IOError:
        print('Could not open JSON file:' + filename, file=sys.stderr)
        sys.exit(1)

    return data

def get_titles(topic):
    url = 'http://en.wikipedia.org/w/api.php'
    values = {
        'action' : 'query',
        'list' : 'search',
        'srwhat' : 'text',
        'srsearch' : topic.encode('utf8'),
        'format' : 'json',
        'srlimit' : '40'
    }

    data = urllib.urlencode(values)
    request = urllib2.Request(url, data)
    response = urllib2.urlopen(request)
    json_response = response.read()
    json_result = json.loads(json_response)

    try:
        results = []
        for result in json_result['query']['search']:
            results.append(result['title'])
    except:
        results = []
        print("ERROR: no title found for topic: " + topic.encode('utf8'))

    return results

def get_graph_string(graph):
    output = StringIO.StringIO()
    graph.draw(output, format = 'svg')
    svg = output.getvalue()
    output.close()

    svg_parser = etree.XMLParser()
    svg_obj = etree.fromstring(svg, svg_parser)

    svg_obj.attrib['width'] = '100%'
    del svg_obj.attrib['height']

    images = svg_obj.findall('.//{http://www.w3.org/2000/svg}image')

    # Convert all image href links to match server
    # For example, anonymous.png becomes static/images/anonymous.png
    # Have to do this because graphviz doesn't allow you to specify the
    # URL to an image, only the file path.
    for image in images:
        image_filename = image.attrib['{http://www.w3.org/1999/xlink}href']
        image_url = url_for('static', filename = 'images/' + image_filename)
        image.attrib['{http://www.w3.org/1999/xlink}href'] = image_url

    return etree.tostring(svg_obj, pretty_print = True)

def get_image_files():
    image_files = []
    image_dir = os.environ['GV_FILE_PATH']

    for root, sub_folders, files in os.walk(image_dir):
        for filename in files:
            actual_file_name = os.path.join(root, filename)
            if filename.endswith('.png'):
                image_files.append(filename)

    return image_files

def build_graph(name, results, topics):
    graph = pgv.AGraph(overlap = 'false', name = name)
    people = get_people()

    for person in results:
        forename, surname = person.lower().split()

        image_file = 'anonymous.png'
        image_files = get_image_files()

        for filename in image_files:
            if string.find(filename, surname) != -1 and string.find(filename, forename) != -1:
                image_file = '%s' % (filename)

        graph.add_node(person, label = person.replace(' ' , '\n'), fontname = 'Helvetica', fixedsize = True, imagescale = True, width = '1.5', height = '1.5', fontcolor = 'white', shape = 'circle', style = 'filled', color = '#303030', URL = url_for('show_person', name = person), image = image_file)

        interests = people[person]['interests']
        for interest in interests:
            if interest in topics:
                color = '#A02020FF'
                shape = 'ellipse'
            else:
                color = '#105060EE'
                shape = 'ellipse'

            label = re.sub('\(.*\)', '', interest)

            graph.add_node(interest, label = label, style = 'filled', fontname = 'Helvetica', shape = shape, color = color, fontcolor = 'white', URL = url_for('show_topic', name = interest))
            graph.add_edge(person, interest, color = '#00000050')

        if 'technologies' in people[person]:
            for technology in people[person]['technologies']:
                if technology in topics:
                    color = '#B01050FF'
                    shape = 'ellipse'
                else:
                    color = '#701050EE'
                    shape = 'ellipse'

                label = re.sub('\(.*\)', '', technology)

                graph.add_node(technology, label = label, style = 'filled', fontname = 'Helvetica', shape = shape, color = color, fontcolor = 'white')
                graph.add_edge(person, technology, color = '#00000050')

    graph.layout(prog = 'neato')

    return graph

@app.route('/')
def index():
    graph_name = 'All people and topics'

    results = set()
    topics = []

    people = get_people()

    for person in people:
        results.add(person)

    graph = build_graph(graph_name, results, topics)
    graph_str = get_graph_string(graph)

    return render_template('graph.html', name = graph_name, node_count = len(graph.nodes()), graph = graph_str)

@app.route('/person/<name>')
def show_person(name):
    graph_name = name + "'s interests"

    results = set()
    topics = []

    results.add(name)

    graph = build_graph(graph_name, results, topics)
    graph_str = get_graph_string(graph)

    return render_template('graph.html', name = graph_name, node_count = len(graph.nodes()), graph = graph_str)

@app.route('/topic/<name>')
def show_topic(name):
    main_topic = name
    graph_name = 'People and topics related to ' + name

    results = set()
    topics = get_titles(name)

    people = get_people()

    for person in people:
        for topic in topics:
            if topic in people[person]['interests']:
                results.add(person)

        if 'technologies' in people[person]:
            for topic in topics:
                if topic in people[person]['technologies']:
                    results.add(person)

    graph = build_graph(graph_name, results, topics)
    graph_str = get_graph_string(graph)

    return render_template('graph.html', name = graph_name, node_count = len(graph.nodes()), graph = graph_str)

@app.route('/topic-search')
def topic_search():
    topic = request.args.get('topic')

    return redirect(url_for('show_topic', name = topic))


if __name__ == "__main__":
    app.run(debug = True)
