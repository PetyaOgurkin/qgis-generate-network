from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessing, QgsFeature, QgsGeometry, QgsPoint, QgsProcessingAlgorithm, QgsProcessingParameterDistance, QgsProcessingParameterFeatureSource, QgsProcessingParameterVectorDestination)
from qgis import processing
import json
from math import (sqrt)

class ExampleProcessingAlgorithm(QgsProcessingAlgorithm):
    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return ExampleProcessingAlgorithm()

    def name(self):
        return 'generatenetwork'

    def displayName(self):
        return self.tr('Сгенерировать сеть')

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                'INPUT',
                self.tr('Входной слой'),
                types=[QgsProcessing.TypeVectorLine]
            )
        )
        
        self.addParameter(
            QgsProcessingParameterDistance(
                'TOLERANCE',
                self.tr('Допустимая погрешность'),
                defaultValue = 0.000001,
                parentParameterName='INPUT'
            )
        )
        
        self.addParameter(
            QgsProcessingParameterVectorDestination(
                'OUTPUT',
                self.tr('Выходной слой')
            )
        )

    res = []

    def distance(self, a, b):
        dx = a[0]-b[0]
        dy = a[1]-b[1]
        dz = a[2]-b[2]
        return sqrt(dx*dx+dy*dy+dz*dz)
        
    def recursive_split(self, segment, features, tolerance):
        [a, b] = json.loads(segment.geometry().asJson())['coordinates']
        ab = self.distance(a, b)
        
        for feature in features:
            [c, d] = json.loads(feature.geometry().asJson())['coordinates']
    
            ac = self.distance(a, c)
            bc = self.distance(b, c)
            ad = self.distance(a, d)
            bd = self.distance(b, d)
            
            if ac > tolerance and bc > tolerance and abs(ac + bc - ab) < tolerance:
                [f1, f2] = self.generate_features(a, c, b)
                self.recursive_split(f1, features, tolerance)
                self.recursive_split(f2, features, tolerance)
                return
            
            if ad > tolerance and bd > tolerance and abs(ad + bd - ab) < tolerance:
                [f1, f2] = self.generate_features(a, d, b)
                self.recursive_split(f1, features, tolerance)
                self.recursive_split(f2, features, tolerance)
                return
        
        self.res.append(segment)
    
        
    def generate_features(self, a, b, c):
        f1 = QgsFeature()
        f2 = QgsFeature()
        f1.setGeometry(QgsGeometry.fromPolyline([QgsPoint(a[0],a[1],a[2]),QgsPoint(b[0],b[1],b[2])]))
        f2.setGeometry(QgsGeometry.fromPolyline([QgsPoint(b[0],b[1],b[2]),QgsPoint(c[0],c[1],c[2])]))
        return [f1, f2]
      

    def processAlgorithm(self, parameters, context, feedback):
        tolerance = self.parameterAsDouble(parameters, 'TOLERANCE', context)

        if feedback.isCanceled():
            return {}
            
        splited_id = processing.run(
            "native:explodelines",
            {
                'INPUT': parameters['INPUT'],
                'OUTPUT': parameters['OUTPUT']
            },
            is_child_algorithm=True,
            context=context,
            feedback=feedback)['OUTPUT']

        if feedback.isCanceled():
            return {}
            
        splited = context.getMapLayer(splited_id)
        features = list(splited.getFeatures())
        
        for feature in features:
            self.recursive_split(feature, features, tolerance)
        
        if feedback.isCanceled():
            return {}
            
        layer = splited.dataProvider()
        layer.truncate()
        layer.addFeatures(self.res)

        return {'OUTPUT': splited_id }