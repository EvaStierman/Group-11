# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ChemicalFireDockWidget
                                 A QGIS plugin
 Helps making desicions when a chemical fire appears
                             -------------------
        begin                : 2017-01-09
        git sha              : $Format:%H$
        copyright            : (C) 2017 by Tu Delft
        email                : e.m.j.stierman@student.tudelft.nl
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from PyQt4 import QtGui, QtCore, uic
from qgis.core import *
from qgis.networkanalysis import *
from qgis.gui import *
import processing

# matplotlib for the charts
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Initialize Qt resources from file resources.py
import resources

import os
import os.path
import random
import csv
import time
import qgis.utils

from PyQt4 import QtGui, Qt, QtCore, QtWebKit
from PyQt4.QtWebKit import QWebPage, QWebView
from PyQt4.QtCore import QUrl
import sys

from . import utility_functions as uf

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'chemical_fire_dockwidget_base.ui'))


class ChemicalFireDockWidget(QtGui.QDockWidget, FORM_CLASS):
    closingPlugin = QtCore.pyqtSignal()
    updateAttribute = QtCore.pyqtSignal(str)
    clickingPoint = QtCore.pyqtSignal(QgsPoint)

    def __init__(self, iface, parent=None):
        """Constructor."""
        super(ChemicalFireDockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        self.graph = QgsGraph()
        self.tied_points = []

########################################################################################################################
#   BUTTONS TAB 1
########################################################################################################################
        self.currentTool = None
        self.selected_building = None
        self.buildings_layer = uf.getLegendLayerByName(self.iface, 'Buildings')
        self.buttonSelectLocation.clicked.connect(self.activateSelection)
        self.buttonConfirmLocation.clicked.connect(self.confirmLocationActions)

########################################################################################################################
#   BUTTONS TAB 2
########################################################################################################################

#        self.buttonSelectVeryToxic.clicked.connect(self.)
#        self.buttonSelectMediumToxic.clicked.connect(self.)
#        self.buttonSelectNotToxic.clicked.connect(self.)
        self.buttonConfirmToxics.clicked.connect(self.confirmToxicActions)

########################################################################################################################
#   BUTTONS TAB 3
########################################################################################################################

        self.SpinBoxAlbrandswaard.valueChanged.connect(self.updateCounter)
        self.spinbox2.valueChanged.connect(self.updateCounter)
        self.SpinBoxHoogstad.valueChanged.connect(self.updateCounter)
        self.SpinBoxKeyenburg.valueChanged.connect(self.updateCounter)
        self.SpinBoxRozenburg.valueChanged.connect(self.updateCounter)
        self.SpinBoxSchiedam.valueChanged.connect(self.updateCounter)
        self.buttonConfirmFireStations.clicked.connect(self.confirmFireStationActions)



    def closeEvent(self, iface, event):
        self.closingPlugin.emit()
        event.accept()


#######################################################################################################################
#   TABBLAD 1
#######################################################################################################################

    def activateSelection(self):
        # make buildings layer active (must pass the layer object, not the name)
        self.canvas.setCurrentLayer(self.buildings_layer)
        # keep current tool to activate it afterwards
        self.currentTool = self.canvas.mapTool()
        self.iface.actionSelect().trigger()
        #   listen to signal that selection was made
        self.buildings_layer.selectionChanged.connect(self.getSelectedBuilding)

    def getSelectedBuilding(self, is_selected, is_deselected):
        # get from list of is_selected
        if is_selected:
            # keep building id for later use
            self.selected_building = self.buildings_layer.selectedFeatures()[0]
            # zoom to the selected buiding
            self.canvas.zoomToSelected()
            self.canvas.zoomOut()
            self.canvas.zoomOut()
            # restore the previous map tool
            self.currentTool.activate()
            # disconnect signal we already have a building
            self.buildings_layer.selectionChanged.disconnect(self.getSelectedBuilding)
            # write building summary info
            #self.writeReport(self.selected_building)
            self.setFireBuilding(self.selected_building)
            self.writeReport()

    def setFireBuilding(self, selected_building):
        delete_fire_building = uf.getLegendLayerByName(self.iface, "FireLocation")
        if delete_fire_building:
            QgsMapLayerRegistry.instance().removeMapLayers([delete_fire_building.id()])
        building_layer = uf.getLegendLayerByName(self.iface, "Buildings")
        fire_building = uf.getLegendLayerByName(self.iface, "FireLocation")
        if not fire_building:
            #self.selected_building = self.buildings_layer.selectedFeatures()[0]
            features = building_layer.selectedFeatures()
            fields_names = [field.name() for field in self.buildings_layer.dataProvider().fields()]
            fields_types = [field.type() for field in self.buildings_layer.dataProvider().fields()]
            fire_building = uf.createTempLayer('FireLocation', 'POLYGON', building_layer.crs().postgisSrid(), fields_names, fields_types)
            fire_building.dataProvider().addFeatures(features)
            fire_building.updateExtents()
            extent = fire_building.extent()
            uf.loadTempLayer(fire_building)
            legend = self.iface.legendInterface()
            legend.setLayerVisible(fire_building, True)
            self.canvas.setExtent(extent)
            self.canvas.refresh()
            self.canvas.zoomOut()
            self.canvas.zoomOut()
            # self.updateRiskReport(risk_buildings)

    def writeReport(self):
        self.reportList1.clear()
        rl = uf.getLegendLayerByName(self.iface, "FireLocation")
        fieldnamesfirelocation = uf.getFieldNames(rl)
        Capneedfield = fieldnamesfirelocation[7]
        Capneeds = uf.getFieldValues(rl, Capneedfield, null=True, selection=False)
        text_Capneeds = str(Capneeds[0][0])
        text_Capneeds2 = "Capacity needed: %s" % str(text_Capneeds)
        self.insertReport1(text_Capneeds2)

        dangersfield = fieldnamesfirelocation[4]
        dangerss = uf.getFieldValues(rl, dangersfield, null=True, selection=False)
        text_dangerss = str(dangerss[0][0])
        text_dangerss2 = "Dangers: %s" % str(text_dangerss)
        self.insertReport1(text_dangerss2)

        substancefield = fieldnamesfirelocation[3]
        substances = uf.getFieldValues(rl, substancefield, null=True, selection=False)
        text_substances = str(substances[0][0])
        text_substances2 = "Substances: %s" % str(text_substances)
        self.insertReport1(text_substances2)

        risklevelfield = fieldnamesfirelocation[2]
        risklevel = uf.getFieldValues(rl, risklevelfield, null=True, selection=False)
        text_risklevel = str(risklevel[0][0])
        text_risklevel2 = "Risk level: %s" % str(text_risklevel)
        self.insertReport1(text_risklevel2)

    def insertReport1(self, item):
        self.reportList1.insertItem(0, item)

    def confirmLocationActions(self):
        self.calculateBuffer(self.selected_building)
        self.setRiskBuildings()
        self.setNearbyWaterAcces()
        self.updateRiskReport()
        self.toSecondTab()

    def calculateBuffer(self, selected_building):

        delete_building_buffer = uf.getLegendLayerByName(self.iface, "BuildingBuffer")
        if delete_building_buffer:
            QgsMapLayerRegistry.instance().removeMapLayers([delete_building_buffer.id()])
        layer = uf.getLegendLayerByName(self.iface, "FireLocation")
        origins = layer.getFeatures()
        if origins > 0:
            cutoff_distance = 400  # self.getBufferCutoff()
            buffers = {}
            for point in origins:
                geom = point.geometry()
                buffers[point.id()] = geom.buffer(cutoff_distance, 12).asPolygon()
            # store the buffer results in temporary layer called "Buffers"
            buffer_layer = uf.getLegendLayerByName(self.iface, "BuildingBuffer")
            # create one if it doesn't exist
            if not buffer_layer:
                attribs = ['id', 'distance']
                types = [QtCore.QVariant.String, QtCore.QVariant.Double]
                buffer_layer = uf.createTempLayer('BuildingBuffer', 'POLYGON', layer.crs().postgisSrid(), attribs,
                                                  types)
                buffer_layer.setLayerName('BuildingBuffer')
                uf.loadTempLayer(buffer_layer)
                legend = self.iface.legendInterface()
                legend.setLayerVisible(buffer_layer, False)

            # insert buffer polygons
            geoms = []
            values = []
            for buffer in buffers.iteritems():
                # each buffer has an id and a geometry
                geoms.append(buffer[1])
                # in the case of values, it expects a list of multiple values in each item - list of lists
                values.append([buffer[0], cutoff_distance])
            uf.insertTempFeatures(buffer_layer, geoms, values)
            self.canvas.refresh()

        delete_water_buffer = uf.getLegendLayerByName(self.iface,"WaterBuffer")
        if delete_water_buffer:
            QgsMapLayerRegistry.instance().removeMapLayers([delete_water_buffer.id()])
        layer = uf.getLegendLayerByName(self.iface, "FireLocation")
        origins = layer.getFeatures()
        if origins > 0:
            cutoff_distance = 250 #self.getBufferCutoff()
            buffers = {}
            for point in origins:
                geom = point.geometry()
                buffers[point.id()] = geom.buffer(cutoff_distance,12).asPolygon()
            # store the buffer results in temporary layer called "Buffers"
            buffer_layer = uf.getLegendLayerByName(self.iface, "WaterBuffer")
            # create one if it doesn't exist
            if not buffer_layer:
                attribs = ['id', 'distance']
                types = [QtCore.QVariant.String, QtCore.QVariant.Double]
                buffer_layer = uf.createTempLayer('WaterBuffer','POLYGON',layer.crs().postgisSrid(), attribs, types)
                buffer_layer.setLayerName('WaterBuffer')
                uf.loadTempLayer(buffer_layer)
                legend = self.iface.legendInterface()
                legend.setLayerVisible(buffer_layer, False)

            # insert buffer polygons
            geoms = []
            values = []
            for buffer in buffers.iteritems():
                # each buffer has an id and a geometry
                geoms.append(buffer[1])
                # in the case of values, it expects a list of multiple values in each item - list of lists
                values.append([buffer[0], cutoff_distance])
            uf.insertTempFeatures(buffer_layer, geoms, values)
            self.canvas.refresh()

        delete_obstacles_buffer = uf.getLegendLayerByName(self.iface, "Obstacles")
        if delete_obstacles_buffer:
            QgsMapLayerRegistry.instance().removeMapLayers([delete_obstacles_buffer.id()])
        layer = uf.getLegendLayerByName(self.iface, "FireLocation")
        origins = layer.getFeatures()
        if origins > 0:
            cutoff_distance = 50  # self.getBufferCutoff()
            buffers = {}
            for point in origins:
                geom = point.geometry()
                buffers[point.id()] = geom.buffer(cutoff_distance, 12).asPolygon()
            # store the buffer results in temporary layer called "Buffers"
            buffer_layer = uf.getLegendLayerByName(self.iface, "Obstacles")
            # create one if it doesn't exist
            if not buffer_layer:
                attribs = ['id', 'distance']
                types = [QtCore.QVariant.String, QtCore.QVariant.Double]
                buffer_layer = uf.createTempLayer('Obstacles', 'POLYGON', layer.crs().postgisSrid(),
                                                  attribs,
                                                  types)
                buffer_layer.setLayerName('Obstacles')
                uf.loadTempLayer(buffer_layer)
                legend = self.iface.legendInterface()
                legend.setLayerVisible(buffer_layer, False)

            # insert buffer polygons
            geoms = []
            values = []
            for buffer in buffers.iteritems():
                # each buffer has an id and a geometry
                geoms.append(buffer[1])
                # in the case of values, it expects a list of multiple values in each item - list of lists
                values.append([buffer[0], cutoff_distance])
            uf.insertTempFeatures(buffer_layer, geoms, values)
            self.canvas.refresh()

    def setRiskBuildings(self):
        delete_risk_building = uf.getLegendLayerByName(self.iface, "RiskBuildings")
        if delete_risk_building:
            QgsMapLayerRegistry.instance().removeMapLayers([delete_risk_building.id()])
        buffer_layer2 = uf.getLegendLayerByName(self.iface, "BuildingBuffer")
        risk_buildings = uf.getLegendLayerByName(self.iface, "RiskBuildings" )
        if not risk_buildings:
            # retrieve buildings inside buffer (inside = True)
            features = uf.getFeaturesByIntersection(self.buildings_layer, buffer_layer2, True)
            # add these buildings to a new temporary layer
            fields_names = [field.name() for field in self.buildings_layer.dataProvider().fields()]
            fields_types = [field.type() for field in self.buildings_layer.dataProvider().fields()]
            risk_buildings = uf.createTempLayer('RiskBuildings','POLYGON',buffer_layer2.crs().postgisSrid(),fields_names, fields_types)
            risk_buildings.dataProvider().addFeatures(features)
            risk_buildings.updateExtents()
            extent = risk_buildings.extent()
            uf.loadTempLayer(risk_buildings)
            legend = self.iface.legendInterface()
            legend.setLayerVisible(risk_buildings, False)
            self.canvas.setExtent(extent)
            self.canvas.refresh()
            self.canvas.zoomOut()
            # self.updateRiskReport(risk_buildings)

    def setNearbyWaterAcces(self):
        delete_risk_building = uf.getLegendLayerByName(self.iface, "NearbyWaterAccess")
        if delete_risk_building:
            QgsMapLayerRegistry.instance().removeMapLayers([delete_risk_building.id()])
        buffer_layer2 = uf.getLegendLayerByName(self.iface, "WaterBuffer")
        water_access_layer = uf.getLegendLayerByName(self.iface, "WaterAccess")
        risk_buildings = uf.getLegendLayerByName(self.iface, "NearbyWaterAccess" )
        if not risk_buildings:
            # retrieve buildings inside buffer (inside = True)
            features = uf.getFeaturesByIntersection(water_access_layer, buffer_layer2, True)
            # add these buildings to a new temporary layer
            fields_names = [field.name() for field in water_access_layer.dataProvider().fields()]
            fields_types = [field.type() for field in water_access_layer.dataProvider().fields()]
            risk_buildings = uf.createTempLayer('NearbyWaterAccess','POINT', water_access_layer.crs().postgisSrid(),fields_names, fields_types)
            risk_buildings.dataProvider().addFeatures(features)
            risk_buildings.updateExtents()
            extent = risk_buildings.extent()
            uf.loadTempLayer(risk_buildings)
            legend = self.iface.legendInterface()
            legend.setLayerVisible(risk_buildings, True)
            self.canvas.setExtent(extent)
            self.canvas.refresh()
            self.canvas.zoomOut()
            # self.updateRiskReport(risk_buildings)

    def updateRiskReport(self):
        risk_building_layer = uf.getLegendLayerByName(self.iface, "RiskBuildings")

    def toSecondTab(self):
        self.tabsWidget.setCurrentIndex(1)

########################################################################################################################
#   TABBLAD 2
########################################################################################################################

    def confirmToxicActions(self):
        self.toThirdTab()

    def toThirdTab(self):
        self.tabsWidget.setCurrentIndex(2)
########################################################################################################################
#   TABBLAD 3
########################################################################################################################

    def confirmFireStationActions(self):
        self.calculateRoutes()
        self.deleteRoutes()
        self.buildNetwork()
        self.calculateRoutes()
        self.toFourthTab()

    def updateCounter(self):
        self.iface.messageBar().pushMessage("updateCounter doet het", level=0, duration=3)
        value = self.SpinBoxAlbrandswaard.value()
        value += self.spinbox2.value()
        value += self.SpinBoxHoogstad.value()
        value += self.SpinBoxKeyenburg.value()
        value += self.SpinBoxRozenburg.value()
        value += self.SpinBoxSchiedam.value()

        value = str(value)
        value2 = "Number of firetrucks selected: %s" % str(value)
        self.insertTruckCounterReport(value2)

    def insertTruckCounterReport(self, item):
        self.iface.messageBar().pushMessage("insertReport doet het", level=0, duration=3)
        self.reportTruckCounter.clear()
        self.reportTruckCounter.insertItem(0, item)

        ################################################################################################################

    def getNetwork(self):
        roads_layer = uf.getLegendLayerByName(self.iface, "Roads")
        if roads_layer:
            # see if there is an obstacles layer to subtract roads from the network
            obstacles_layer = uf.getLegendLayerByName(self.iface, "Obstacles")
            if obstacles_layer:
                # retrieve roads outside obstacles (inside = False)
                features = uf.getFeaturesByIntersection(roads_layer, obstacles_layer, False)
                # add these roads to a new temporary layer
                road_network = uf.createTempLayer('Temp_Network', 'LINESTRING', roads_layer.crs().postgisSrid(), [], [])
                road_network.dataProvider().addFeatures(features)
            else:
                road_network = roads_layer
            return road_network
        else:
            return

    def buildNetwork(self):
        self.network_layer = self.getNetwork()
        if self.network_layer:
            # get the points to be used as origin and destination
            # in this case gets the centroid of the selected features
            selected_sources = self.getSelectedLayer().selectedFeatures()
            source_points = [feature.geometry().centroid().asPoint() for feature in selected_sources]
            # build the graph including these points
            if len(source_points) > 1:
                self.graph, self.tied_points = uf.makeUndirectedGraph(self.network_layer, source_points)
                # the tied points are the new source_points on the graph
                if self.graph and self.tied_points:
                    text = "network is built for %s points" % len(self.tied_points)
                    self.insertReport(text)
        return

    def calculateRoutes(self):
        # get the building point, and the fire station points
        new_points = []
        building_names = []
        # selected building
        fire_location = uf.getLegendLayerByName(self.iface, "FireLocation")
        new_points.append(fire_location.geometry().centroid().asPoint())
        building_names.append(fire_location.id())
        # fire stations
        fire_stations_layer = uf.getLegendLayerByName(self.iface, "Firestations")
        for f in fire_stations_layer.getFeatures():
            building_names.append(f.attribute('name'))
            new_points.append(f.geometry().centroid().asPoint())
        # build the graph, which returns the tied points.
        # this is a list of nodes on the graph that are used to calculate routes.
        graph, tied_points = uf.makeUndirectedGraph(self.roads_layer, new_points)
        # this next part calculates the routes betwen building and fire stations
        # store the route results in temporary layer called "Routes"
        roads_layer = uf.getLegendLayerByName(self.iface, "Roads")
        routes_layer = uf.getLegendLayerByName(self.iface, "Routes")
        # create one if it doesn't exist
        if not routes_layer:
            attributes = ['id', 'origin', 'destination', 'distance', 'time']
            types = [QtCore.QVariant.String, QtCore.QVariant.String, QtCore.QVariant.String, QtCore.QVariant.String,
                     QtCore.QVariant.String]
            routes_layer = uf.createTempLayer('Routes', 'LINESTRING', roads_layer.crs().postgisSrid(), attributes,
                                              types)
            uf.loadTempLayer(routes_layer)
        provider = routes_layer.dataProvider()
        # destination is always the first point in the list
        destination = 0
        # iterate through fire stations
        fire_station_info = {}
        for origin in new_points[1:]:
            path = uf.calculateRouteDijkstra(graph, tied_points, origin, destination)
            geom = QgsGeometry.fromPolyline(path)
            feat = QgsFeature()
            feat.setGeometry(geom)
            length = geom.length()
            # time assumes 60km/h
            # and converts seconds to minutes/seconds
            m, s = divmod(length * 3600 / 60000.0, 60)
            time = '%02d:%02s' % (m, s)
            attributes = [str(origin), building_names[0], building_names[origin], str(length), time]
            feat.setAttributes(attributes)
            provider.addFeatures([feat])
            # keep fire station info for report
            fire_station_info[building_names[origin]] = time
        provider.updateExtents()
        # update firestations report (not implemented here)
        self.updateFirestations(fire_station_info)

    def deleteRoutes(self):
        routes_layer = uf.getLegendLayerByName(self.iface, "Routes")
        if routes_layer:
            ids = uf.getAllFeatureIds(routes_layer)
            routes_layer.startEditing()
            for id in ids:
                routes_layer.deleteFeature(id)
            routes_layer.commitChanges()

    def toFourthTab(self):
        self.tabsWidget.setCurrentIndex(3)