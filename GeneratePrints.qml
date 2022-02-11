import UM 1.1 as UM
import QtQuick 2.2
import QtQuick.Controls 1.1


UM.Dialog
{
    id: base

    width: 600
    height: 600
    minimumWidth: 200
    minimumHeight: 200

    // Prevent ENTER from closing the dialog
    function accept() {
    }
    Column {
        spacing: 5

        Label {
            text: "WARNING: Make sure there is only a single selected object on your build plate"
        }
        Label {
            text: "WARNING: Make sure you have valid min/max entered for all settings below."
        }
        ListView {
            id: listview
            width: 180; height: 200
            model: manager.ParametersListModel
            delegate: Row {
                spacing: 5
                height: 40
                Label {
                    text: name + " [" + type + "]"
                }
                Label {
                    text: "min:"
                    visible: type == "int" || type == "float"
                }
                TextField {
                    id: min_box
                    text: min
                    onTextChanged: min = text
                    visible: type == "int" || type == "float"
                }
                Label {
                    text: "max:"
                    visible: type == "int" || type == "float"
                }
                TextField {
                    id: max_box
                    text: max
                    onTextChanged: max = text
                    visible: type == "int" || type == "float"
                }
                Label {
                    text: "Enum Options (comma separated): "
                    visible: type == "enum"
                }
                TextField {
                    id: choices_box
                    text: choices
                    onTextChanged: choices = text
                    visible: type == "enum"
                }
                Button {
                    id: remove_button
                    text: "Remove"
                    onClicked:
                    {
                      listview.model.remove(index)
                    }
                }
            }
        }
        Label {
            id: "valid_settings_names"
            text: ""
        }
        Row {
            spacing: 5
            Label {
                text: "Setting name:"
            }
            TextField {
                id: setting_name
            }
            Button {
                id: setting_add_button
                text: "Add to Tuned Settings"
                onClicked: {
                    if (manager.validKeys.includes(setting_name.text)) {
                        if(!listview.model.contains("name", setting_name.text)) {
                            listview.model.append({
                                "name": setting_name.text,
                                "type": manager.getSettingsType(setting_name.text),
                                "min": "",
                                "max":"",
                                "choices": manager.getEnumSettingsOptions(setting_name.text).join()})
                        }
                    }
                 }
            }
        }
        Row {
            spacing: 5
            Label {
                text: "Model Spacing: "
            }
            TextField {
                id: model_spacing
                text: "8"
            }
            Label {
                text: "mm"
            }
        }
        Label {
            text: "WARNING: Generating test prints will forget any previous unscored print."
        }
        Button {
            text: "Generate new set of Test Prints"
            onClicked: {
                if(manager.validGeneratePrintOptions()) {
                    manager.generatePrints(model_spacing.text)
                    base.close()
                }
            }
        }
    }
    onVisibleChanged: {
        valid_settings_names.text = "Valid (visible) settings names: " + manager.validKeys
    }
}