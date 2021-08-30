"""
Model exported as python.
Name : Huisnr uitlijnen
Group : stratenplan
With QGIS : 31606
"""

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsExpression
import processing


class HuisnrUitlijnen(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer('CrabAdr', 'CrabAdr', types=[QgsProcessing.TypeVectorPoint], defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('Gbg', 'Gbg', types=[QgsProcessing.TypeVectorPolygon], defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('Wvb', 'Wvb', types=[QgsProcessing.TypeVectorLine], defaultValue=None))
        self.addParameter(QgsProcessingParameterFeatureSink('Huisnr', 'huisnr', type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, supportsAppend=True, defaultValue='TEMPORARY_OUTPUT'))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(10, model_feedback)
        results = {}
        outputs = {}

        # Koppel attributen op basis van plaats
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'INPUT': parameters['Gbg'],
            'JOIN': parameters['CrabAdr'],
            'JOIN_FIELDS': [''],
            'METHOD': 0,
            'PREDICATE': [0],
            'PREFIX': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['KoppelAttributenOpBasisVanPlaats'] = processing.run('native:joinattributesbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Polygonen naar lijnen
        alg_params = {
            'INPUT': outputs['KoppelAttributenOpBasisVanPlaats']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['PolygonenNaarLijnen'] = processing.run('native:polygonstolines', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Lijnen uitvergroten/explode
        alg_params = {
            'INPUT': outputs['PolygonenNaarLijnen']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['LijnenUitvergrotenexplode'] = processing.run('native:explodelines', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Zwaartepunten/centroids
        alg_params = {
            'ALL_PARTS': False,
            'INPUT': outputs['LijnenUitvergrotenexplode']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Zwaartepuntencentroids'] = processing.run('native:centroids', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # Koppel attributen op dichtstbijzijnde
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'FIELDS_TO_COPY': [''],
            'INPUT': outputs['Zwaartepuntencentroids']['OUTPUT'],
            'INPUT_2': parameters['Wvb'],
            'MAX_DISTANCE': None,
            'NEIGHBORS': 1,
            'PREFIX': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['KoppelAttributenOpDichtstbijzijnde'] = processing.run('native:joinbynearest', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # Geometrie met expressie
        alg_params = {
            'EXPRESSION': 'make_line(make_point ( \"feature_x\" , \"feature_y\" ),make_point( \"nearest_x\" , \"nearest_y\" ))',
            'INPUT': outputs['KoppelAttributenOpDichtstbijzijnde']['OUTPUT'],
            'OUTPUT_GEOMETRY': 1,
            'WITH_M': False,
            'WITH_Z': False,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['GeometrieMetExpressie'] = processing.run('native:geometrybyexpression', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}

        # Automatisch ophogend veld toevoegen
        alg_params = {
            'FIELD_NAME': 'RANK',
            'GROUP_FIELDS': QgsExpression('\'ID\'').evaluate(),
            'INPUT': outputs['GeometrieMetExpressie']['OUTPUT'],
            'SORT_ASCENDING': True,
            'SORT_EXPRESSION': QgsExpression('\'distance\'').evaluate(),
            'SORT_NULLS_FIRST': False,
            'START': 1,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['AutomatischOphogendVeldToevoegen'] = processing.run('native:addautoincrementalfield', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(7)
        if feedback.isCanceled():
            return {}

        # Uitnemen op attribuut
        alg_params = {
            'FIELD': 'RANK',
            'INPUT': outputs['AutomatischOphogendVeldToevoegen']['OUTPUT'],
            'OPERATOR': 0,
            'VALUE': '1',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['UitnemenOpAttribuut'] = processing.run('native:extractbyattribute', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(8)
        if feedback.isCanceled():
            return {}

        # Lijnen verlengen
        alg_params = {
            'END_DISTANCE': 0,
            'INPUT': outputs['UitnemenOpAttribuut']['OUTPUT'],
            'START_DISTANCE': 4,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['LijnenVerlengen'] = processing.run('native:extendlines', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(9)
        if feedback.isCanceled():
            return {}

        # Geometrie met expressie
        alg_params = {
            'EXPRESSION': ' start_point( $geometry)',
            'INPUT': outputs['LijnenVerlengen']['OUTPUT'],
            'OUTPUT_GEOMETRY': 2,
            'WITH_M': False,
            'WITH_Z': False,
            'OUTPUT': parameters['Huisnr']
        }
        outputs['GeometrieMetExpressie'] = processing.run('native:geometrybyexpression', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Huisnr'] = outputs['GeometrieMetExpressie']['OUTPUT']
        return results

    def name(self):
        return 'Huisnr uitlijnen'

    def displayName(self):
        return 'Huisnr uitlijnen'

    def group(self):
        return 'stratenplan'

    def groupId(self):
        return 'stratenplan'

    def createInstance(self):
        return HuisnrUitlijnen()
