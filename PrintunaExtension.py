import copy
import os.path
import pickle
from typing import Optional, List

from PyQt5.QtCore import pyqtProperty, pyqtSlot, QObject
from UM.Application import Application
from UM.Extension import Extension
from UM.Logger import Logger
from UM.Math.Vector import Vector
from UM.Operations.AddSceneNodeOperation import AddSceneNodeOperation
from UM.Operations.GroupedOperation import GroupedOperation
from UM.Operations.RemoveSceneNodeOperation import RemoveSceneNodeOperation
from UM.Operations.SetTransformOperation import SetTransformOperation
from UM.PluginRegistry import PluginRegistry
from UM.Scene.SceneNode import SceneNode
from UM.Scene.Selection import Selection

from .GenericListModel import GenericListModel

parent_dir = os.path.abspath(os.path.dirname(__file__))
vendor_dir = os.path.join(parent_dir, 'vendor')
import sys

sys.path.append(vendor_dir)
import optuna


class PrintunaExtension(Extension, QObject):
    def __init__(self, parent: Optional[QObject] = None):
        QObject.__init__(self, parent)
        Extension.__init__(self)

        self._application = Application.getInstance()

        self._parameters_list_model = GenericListModel(["name", "type", "min", "max", "choices"])
        self._active_trials_model = GenericListModel(["id", "score"])
        self.optuna_study = None
        self.resetStudy()

        self.setMenuName("PrinTuna")

        self.addMenuItem("Reset Study", self.resetStudy)
        self.addMenuItem("Generate Prints", self.showGeneratePrints)
        self.addMenuItem("Score Prints", self.showScorePrints)

        self.generate_prints_window = None
        self.score_prints_window = None

        Application.getInstance().workspaceLoaded.connect(self.workspaceLoaded)

    def resetStudy(self):
        self.optuna_study = optuna.create_study(direction="maximize")
        self._active_trials_model.clear()

    def showGeneratePrints(self):
        if not self.generate_prints_window:  # Don't create more than one.
            self.generate_prints_window = self._createDialog("GeneratePrints.qml")

        # If none are selected, prefill with all valid settings
        if len(self._parameters_list_model.items) == 0:
            for key in self.validKeys:
                self._parameters_list_model.append(
                    {"name": key,
                     "type": self.getSettingsType(key),
                     "min": "",
                     "max": "",
                     "choices": ','.join(self.getEnumSettingsOptions(key))})
        self.generate_prints_window.show()

    def configureSingleObject(self, node):
        container = node.callDecoration("getStack").getContainer(0)
        trial = self.optuna_study.ask()
        self._active_trials_model.append({"id": trial.number, "score": ""})
        for setting in self._parameters_list_model.items:
            name = setting["name"]
            type = setting["type"]

            if type == "float":
                value = trial.suggest_float(name, float(setting["min"]), float(setting["max"]))
            elif type == "int":
                value = trial.suggest_int(name, int(setting["min"]), int(setting["max"]))
            elif type == "enum":
                choices = [s.strip() for s in setting["choices"].split(',')]
                value = trial.suggest_categorical(name, choices)
            elif type == "bool":
                value = trial.suggest_categorical(name, [False, True])
            container.setProperty(name, "value", value)

    @pyqtSlot(str)
    def generatePrints(self, model_spacing):
        global_container_stack = self._application.getGlobalContainerStack()
        if not global_container_stack:
            Logger.log("e", "PrinTuna failed to load global container stack.")
            return

        nodes_list = self._getAllSelectedNodes()
        scene_root = self._application.getController().getScene().getRoot()

        if len(nodes_list) != 1:
            Logger.log("e", "Printuna requires a single selected object.")
            return

        self._active_trials_model.clear()

        node = nodes_list[0]

        node_box = node.getBoundingBox()

        disallowed_edge = self._application.getBuildVolume().getEdgeDisallowedSize() + 2  # Allow for some rounding errors
        plate_width, plate_depth = (global_container_stack.getProperty("machine_width", "value"),
                                    global_container_stack.getProperty("machine_depth", "value"))
        min_x = -plate_width / 2 + disallowed_edge + node_box.width / 2
        min_y = -plate_depth / 2 + disallowed_edge + node_box.depth / 2

        min_spacing = float(model_spacing)

        max_x = -min_x
        max_y = -min_y

        nodes = []
        op = GroupedOperation()
        op.addOperation(RemoveSceneNodeOperation(node))
        x = min_x
        while x < max_x:
            y = min_y
            while y < max_y:
                new_node = copy.deepcopy(node)
                build_plate_number = node.callDecoration("getBuildPlateNumber")
                new_node.callDecoration("setBuildPlateNumber", build_plate_number)
                for child in new_node.getChildren():
                    child.callDecoration("setBuildPlateNumber", build_plate_number)
                position = Vector(x, node_box.height / 2, y)
                op.addOperation(AddSceneNodeOperation(new_node, scene_root))
                op.addOperation(SetTransformOperation(new_node, translation=position))

                self.configureSingleObject(new_node)
                nodes.append(new_node)
                y += node_box.depth + min_spacing
            x += node_box.width + min_spacing
        op.push()

    def showScorePrints(self):
        if not self.score_prints_window:  # Don't create more than one.
            self.score_prints_window = self._createDialog("ScorePrints.qml")
        self.score_prints_window.show()

    @pyqtSlot()
    def scorePrints(self):
        for item in self._active_trials_model.items:
            id = item["id"]
            score = float(item["score"])
            self.optuna_study.tell(id, score)

        self._active_trials_model.clear()

    def workspaceLoaded(self):
        metadata_storage = Application.getInstance().getWorkspaceMetadataStorage()
        stored_data = metadata_storage.getPluginMetadata("printuna")
        if stored_data:
            self.optuna_study, settings, trials = pickle.loads(stored_data)
            self._parameters_list_model.clear()
            for setting in settings:
                self._parameters_list_model.append(setting)
            self._active_trials_model.clear()
            for trial in trials:
                self._active_trials_model.append({"id": trial, "score": ""})

    def _createDialog(self, name):
        qml_file_path = os.path.join(PluginRegistry.getInstance().getPluginPath(self.getPluginId()), name)
        component = Application.getInstance().createQmlComponent(qml_file_path, {"manager": self})

        return component

    def _getAllSelectedNodes(self) -> List[SceneNode]:
        selection = Selection.getAllSelectedObjects()[:]
        if selection:
            deep_selection = []  # type: List[SceneNode]
            for selected_node in selection:
                if selected_node.hasChildren():
                    deep_selection = deep_selection + selected_node.getAllChildren()
                if selected_node.getMeshData() != None:
                    deep_selection.append(selected_node)
            if deep_selection:
                return deep_selection

        return []

    @pyqtProperty(QObject, constant=True)
    def ParametersListModel(self):
        return self._parameters_list_model

    @pyqtProperty(QObject, constant=True)
    def ActiveTrialsModel(self):
        return self._active_trials_model

    @pyqtProperty('QStringList')
    def validKeys(self):
        nodes = self._getAllSelectedNodes()
        if nodes:
            return list(nodes[0].callDecoration('getStack').getContainer(0).getAllKeys())
        return []

    @pyqtSlot(str, result="QString")
    def getSettingsType(self, key):
        nodes = self._getAllSelectedNodes()
        if nodes:
            return nodes[0].callDecoration('getStack').getSettingDefinition(key).type
        return ""

    @pyqtSlot(str, result='QStringList')
    def getEnumSettingsOptions(self, key):
        nodes = self._getAllSelectedNodes()
        if nodes:
            return list(nodes[0].callDecoration('getStack').getSettingDefinition(key).options.keys())
        return []

    @pyqtSlot(result='bool')
    def validGeneratePrintOptions(self):
        try:
            for setting in self._parameters_list_model.items:
                name = setting["name"]
                type = setting["type"]
                if type == "float":
                    float(setting["min"])
                    float(setting["max"])
                elif type == "int":
                    int(setting["min"])
                    int(setting["max"])
                elif type == "enum":
                    choices = [s.strip() for s in setting["choices"].split(',')]
                    for choice in choices:
                        if choice not in self.getEnumSettingsOptions(name):
                            return False
        except ValueError:
            return False
        return True

    @pyqtSlot(result='bool')
    def validScoredPrints(self):
        try:
            for item in self._active_trials_model.items:
                float(item["score"])
        except ValueError:
            return False
        return True