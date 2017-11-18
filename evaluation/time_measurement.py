#!/bin/python3

import psycopg2
import sys
import random
import time

import plotly
import plotly.graph_objs as go
import numpy as np

STD_USER = 'postgres'
STD_PASSWORD = 'postgres'
STD_HOST = 'localhost'
STD_DB_NAME = 'imdb'

VEC_TABLE_NAME = 'google_vecs_norm'


QUERY_SET_FULL = [('brute-force', 'SELECT v2.word FROM google_vecs_norm AS v2 ORDER BY cosine_similarity_norm({!s}, v2.vector) DESC FETCH FIRST {:d} ROWS ONLY'),
('pq search', 'SELECT * FROM pq_search({!s}, {:d}) AS (id integer, distance float4);'),
('ivfadc search', 'SELECT * FROM ivfadc_search({!s}, {:d}) AS (id integer, distance float4);')]
QUERY_SET_TEST = [
('pq_search', 'SELECT * FROM pq_search({!s}, {:d}) AS (id integer, distance float4);'),
('ivfadc_search', 'SELECT * FROM ivfadc_search({!s}, {:d}) AS (id integer, distance float4);')]


def serialize_vector(vector):
    result = ''
    for elem in vector:
        result += (str(elem) + ',')
    return '\'{{{!s}}}\'::float4[]'.format(result[:-1])

def get_vector_dataset_size(cur):
    cur.execute('SELECT count(*) FROM {!s};'.format(VEC_TABLE_NAME))
    return cur.fetchone()[0]
def get_samples(con, cur, number, size):
    rnds = ''
    for i in range(number):
        rnds += (str(random.randint(1, size)) + ',')
    rnds = rnds[:-1]
    query = 'SELECT vector from {!s} WHERE id in ({!s})'.format(VEC_TABLE_NAME, rnds)
    cur.execute(query)
    return [x[0] for x in cur.fetchall()]


def measurement(cur, con, query_set, k, samples):
    results = {}
    count = 0
    for (name, query) in query_set:
        results[name] = []
        print('Start Test for', name)
        for sample in samples:
            vector = serialize_vector(sample)
            rendered_query = query.format(vector, k)
            start = time.time()
            cur.execute(rendered_query)
            result = cur.fetchall()
            end = time.time()
            results[name].append((end-start))
            count += 1
            print('Iteration', count, 'completed')
    return results

def plot_graph(measured_data):
    data = []
    for i, key in enumerate(measured_data.keys()):
        trace = go.Scatter(
            name=key,
            y=measured_data[key],
            x=[i]*len(measured_data[key])
        )
    data = [go.Bar(
            x=list(measured_data.keys()),
            y=[np.mean(measured_data[x]) for x in measured_data.keys()]
    )]
    layout = go.Layout(yaxis= dict(title='time in seconds', titlefont=dict(size=20), tickfont=dict(size=20)))
    fig = go.Figure(data=data, layout=layout)
    plotly.offline.plot(fig, filename="tmp.html", auto_open=True)
    return None

def main(argc, argv):
    k = 5
    number = 10
    if argc == 3:
        k = int(argv[1])
        number = int(argv[2])

    try:
        con = psycopg2.connect("dbname='" + STD_DB_NAME + "' user='" + STD_USER + "' host='" + STD_HOST + "' password='" + STD_PASSWORD + "'")
    except:
        print('Can not connect to database')
        return
    cur = con.cursor()

    data_size = get_vector_dataset_size(cur)
    samples = get_samples(con, cur, number, data_size)
    values = measurement(cur, con, QUERY_SET_FULL, k, samples)
    plot_graph(values)

    print('Parameters k:', k, 'Number of Queries:', number)
    for test in values.keys():
        print('TEST', test, 'TIME_SUM:', sum(values[test]), 'TIME_SINGLE:', sum(values[test])/number)

if __name__ == "__main__":
	main(len(sys.argv), sys.argv)