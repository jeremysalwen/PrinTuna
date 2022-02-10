import UM 1.1 as UM
import QtQuick 2.2
import QtQuick.Controls 1.1


UM.Dialog
{
    id: base

    width: 600
    height: 800
    minimumWidth: 200
    minimumHeight: 200

    Column {
        spacing: 5
        Label {
            text: "Enter scores for each object printed on the last generated grid."
        }
        Label {
            text: "Objects are ordered from back left, to front left, then back second-to-left, to front second-to-left, etc."
        }
        ListView {
            id: listview
            width: 180; height: 500
            model: manager.ActiveTrialsModel
            delegate: Row {
                spacing: 5
                height: 40
                Label {
                    text: "Score for Trial "+id+":"
                }
                TextField {
                    id: score_box
                    text: score
                    onEditingFinished: score = text
                }

            }
        }
        Label {
            text: "WARNING: All scores must be entered."
        }
        Button {
            text: "Submit Scores"
            onClicked: {
                manager.scorePrints()
                base.close()
            }
        }
    }
}