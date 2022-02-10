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

    Column {
        spacing: 5

        Label {
            text: "POTENTIAL CRASH: setting names must be exactly right and min/max must be filled with valid numbers."
        }
        ListView {
            id: listview
            width: 180; height: 200
            model: manager.ParametersListModel
            delegate: Row {
                spacing: 5
                height: 40
                Label {
                    text: name
                }
                Label {
                    text: "min:"
                }
                TextField {
                    id: min_box
                    text: min
                    onEditingFinished: min = text
                }
                Label {
                    text: "max:"
                }
                TextField {
                    id: max_box
                    text: max
                    onEditingFinished: max = text
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
                     listview.model.append({ "name": setting_name.text, "min": "", "max":""})
                 }
            }
        }
        Label {
            text: "WARNING: Generating test prints requires exactly one object to be selected or it will do nothing."
        }
        Label {
            text: "WARNING: Generating test prints will forget any previous unscored print."
        }
        Button {
            text: "Generate new set of Test Prints"
            onClicked: {
                manager.generatePrints()
                base.close()
            }
        }
    }
}