#!/usr/bin/env python3
# coding=utf-8

# Copyright (C) 2018  Paweł Widera, Tom Merritt-Smith
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details:
# http://www.gnu.org/licenses/gpl.txt
"""
Shows the relative demand for source / destination stations of the
Newcastle metro at different times of a day (6:00 a.m. to midnight).
Uses Nexus survey data and station coordinates from Open Street Map.

"""
import os
import folium
import pandas

from lxml import etree


def convert(text, field):
	metro_stop = text.split("|")[-field][3:]
	if metro_stop.startswith(" "):
		metro_stop = metro_stop[4:-5]
	if metro_stop.startswith("- "):
		metro_stop = metro_stop[5:-5]
	if metro_stop.startswith("Monument"):
		metro_stop = "Monument"
	if metro_stop.startswith["Central"]:
		metro_stop = "Central Station"
	return metro_stop


def parse_survey():
	file_names = os.listdir("data")
	file_names = filter(lambda x: x.startswith("Metro"), file_names)

	frames = []
	for name in file_names:
		frame = pandas.read_excel(os.path.join("data", name))
		frames.append(frame)

	nexus = pandas.concat(frames, ignore_index=True)
	nexus.dropna(axis=1, thresh=int(0.95 * len(nexus)), inplace=True)
	missing = nexus[nexus.Time.isnull() | nexus.OnOff.isnull()].index
	nexus.drop(missing, inplace=True)

	data = pandas.DataFrame({
		"time": pandas.to_datetime(nexus.Time),
		"section": nexus.section_id,
		"source": nexus.OnOff.apply(lambda x: convert(x, 2)),
		"destination": nexus.OnOff.apply(lambda x: convert(x, 1))
	})

	data.to_hdf("data/nexus.hdf", "nexus", complib="blosc", complevel=9)
	return data


def parse_coordinates():
	tree = etree.parse("data/metro_stations.xml")
	stations = {}
	for node in tree.findall("node"):
		name = node.xpath("tag[@k='name']/@v")
		if name:
			name = name[0]
			stations[name] = [float(node.attrib[x]) for x in ["lat", "lon"]]
	return stations


def read_data():
	try:
		data = pandas.read_hdf("data/nexus.hdf", "nexus")
	except (IOError, KeyError):
		data = parse_survey()

	stations = parse_coordinates()
	return data, stations


def make_map(data, stations, start, end, travel):
	subset = data[data.time.apply(lambda x: start <= x.hour < end)]
	demand = subset.groupby(travel).time.count()
	percentages = 100 * demand / demand.sum()
	sizes = 3 + 20 * demand / demand.max()

	osm = folium.Map(stations["Hebburn"], zoom_start=12)

	for station in (s for s in stations if s in demand):
		popup = "{0} ({1:.1f}%)".format(station, percentages[station])
		folium.CircleMarker(stations[station], popup=popup, radius=sizes[station],
			color="black", fill_color="red", fill=True).add_to(osm)

	file_name = "map_{0}_{1}-{2}.html".format(travel, start, end)
	osm.save(os.path.join("maps", file_name))


data, stations = read_data()
if not os.path.exists("maps"):
	os.mkdir("maps")

for travel in ["source", "destination"]:
	for hour in range(6, 24, 3):
		make_map(data, stations, hour, hour + 3, travel)
