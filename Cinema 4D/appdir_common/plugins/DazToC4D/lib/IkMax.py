from ntpath import join
import sys
import os
import c4d
from c4d import gui, documents

from .CustomCmd import Cinema4DCommands as dzc4d
from .Utilities import dazToC4Dutils
from .CustomIterators import TagIterator
from .DazRig import DazRig, JointFixes
from . import Utilities
from .RigDictionary import is_g9, rig_label, database

def applyDazIK(var):
    doc = documents.GetActiveDocument()
    global dazName
    meshName = Utilities.get_daz_name()
    dazName = meshName + "_"

    dazToC4Dutils().guidesToDaz()  # Auto Generate Guides
    dazToC4Dutils().cleanJointsDaz()  # Some adjustments to Daz Rig...
    # Ikmax stuff...----------------------
    ikmGenerator().makeRig()

    # Need to refactor before using.
    jnt = JointFixes()
    jnt.store_joint_orientations(var.dtu)
    jnt.fix_rig_joints(var.c_joints)

    suffix = "___R"
    objArm = doc.SearchObject(dazName + rig_label("jCollar"))
    objLeg = doc.SearchObject(dazName + rig_label("jUpLeg"))

    ikmGenerator().makeIKcontrols()
    ikmaxUtils().mirrorObjects(objArm, suffix)
    ikmaxUtils().mirrorObjects(objLeg, suffix)
    ikmGenerator().makeChildKeepPos(
        dazName + rig_label("Foot_Platform___R"), dazName + rig_label("Foot_PlatformBase___R")
    )
    ikmGenerator().makeChildKeepPos(
        dazName + rig_label("Foot_PlatformBase___R"), dazName + "IKM_Controls"
    )

    DazRig(dazName).dazEyesLookAtControls()

    # ------------------------------------

    dazToC4Dutils().cleanJointsDaz("Right")

    dazToC4Dutils().constraintJointsToDaz()
    dazToC4Dutils().constraintJointsToDaz("Right")
    if doc.SearchObject(dazName + rig_label("ForearmTwist_ctrl")):
        dazToC4Dutils().twistBoneSetup()  # TwistBone Setup
        obj = doc.SearchObject(dazName + rig_label("ForearmTwist_ctrl"))
        obj[c4d.ID_BASEOBJECT_REL_ROTATION, c4d.VECTOR_X] = 0
        obj = doc.SearchObject(dazName + rig_label("ForearmTwist_ctrl___R"))
        obj[c4d.ID_BASEOBJECT_REL_ROTATION, c4d.VECTOR_X] = 0
        ikmGenerator().constraintObj(rig_label("lForearmTwist"), dazName + rig_label("ForearmTwist_ctrl"))
        ikmGenerator().constraintObj(rig_label("rForearmTwist"), dazName + rig_label("ForearmTwist_ctrl___R"))
        dazToC4Dutils().fixConstraints()
        dazToC4Dutils().zeroTwistRotationFix(
            dazName + rig_label("ForearmTwist_ctrl"), rig_label("lForearmTwist")
        )
        dazToC4Dutils().zeroTwistRotationFix(
            dazName + rig_label("ForearmTwist_ctrl___R"), rig_label("rForearmTwist")
        )

    ikmaxUtils().freezeChilds(dazName + "IKM_Controls")
    ikmaxUtils().freezeChilds(dazName + rig_label("jPelvis"))

    dazToC4Dutils().addProtection()  # Foot controls lock position, allow rotations.
    ikmaxUtils().hideGuides(1)
    dazToC4Dutils().hideRig()
    dzc4d.deselect_all()  # Deselect All
    guides = doc.SearchObject(dazName + "_IKM-Guides")
    if guides:
        guides.Remove()  # REMOVE GUIDES
    c4d.EventAdd()


class ikmaxUtils:
    def iterateObjChilds(self, obj):
        parent = obj  # stores the active object in a 'parent' variable, so it always stays the same
        children = []  # create an empty list to store children

        while (
            obj != None
        ):  # while there is a object (the "walker" function will return None at some point and that will exit the while loop)
            obj = self.walker(
                parent, obj
            )  # set the obj to the result of the walker function
            if obj != None:  # if obj is not None
                children.append(obj)  # append that object to the children list

        return children

    def walker(self, parent, obj):
        if not obj:
            return  # if obj is None, the function returns None and breaks the while loop
        elif obj.GetDown():  # if there is a child of obj
            return obj.GetDown()  # the walker function returns that child
        while (
            obj.GetUp() and not obj.GetNext() and obj.GetUp() != parent
        ):  # if there is a parent of the obj and there isn't another object after the obj and the parent object is not the same object stored in "parent"
            obj = obj.GetUp()  # it set's the current obj to that parent
        return (
            obj.GetNext()
        )  # and return the object that's after that parent, not under, after :)

    def setProtection(self, obj, value):
        # value = 0:None 1:Lock
        # doc = documents.GetActiveDocument()
        # obj = doc.SearchObject(objName)
        currentTag = None
        if obj:
            currentTag = obj.GetFirstTag()
        if currentTag != None and "Protection" in currentTag.GetName():
            currentTag[c4d.PROTECTION_P] = value
            currentTag[c4d.PROTECTION_S] = value
            currentTag[c4d.PROTECTION_R] = value
        c4d.EventAdd()

    def setProtectionChildren(self, obj, value):
        doc = c4d.documents.GetActiveDocument()
        # obj = doc.SearchObject(objName)
        # obj = objName
        caca = self.iterateObjChilds(obj)
        for c in caca:
            self.setProtection(c, value)

    def makeChildKeepPos(self, objChild, objParent):
        try:
            origPos = objChild.GetMg()
            objChild.InsertUnder(objParent)
            objChild.SetMg(origPos)
        except:
            print("IKM: Obj parent skip...")

    def GetDistance(self, Pmin, Pmax):
        offset = 0 - Pmin
        distance = (Pmax + offset) - (Pmin + offset)

        return distance

    def mirrorObjects(self, obj, suffix):
        doc = documents.GetActiveDocument()
        objActive = doc.GetActiveObject()
        objMirror = doc.SearchObject(obj.GetName() + suffix)
        jointPelvis = doc.SearchObject(dazName + rig_label("jPelvis"))
        try:
            objMirror.Remove()
        except:
            pass
        try:
            doc.SetActiveObject(obj)
            c4d.CallCommand(1019953)  # Mirror Tool
            tool = c4d.plugins.FindPlugin(doc.GetAction(), c4d.PLUGINTYPE_TOOL)

            if tool is not None:
                tool[c4d.ID_CA_MIRROR_TOOL_ORIGIN] = 4  # 4=Obj
                tool[c4d.ID_CA_MIRROR_TOOL_COORDS] = 1  # 1=local
                tool[
                    c4d.ID_CA_MIRROR_TOOL_AXIS
                ] = 2  # Axes Propertie: XY #If Rotate is selected.. Wrong rotations!
                tool[c4d.ID_CA_MIRROR_TOOL_POST] = suffix
                tool[c4d.ID_CA_MIRROR_TOOL_OBJECT_LINK] = jointPelvis
                tool[
                    c4d.ID_CA_MIRROR_TOOL_TARGET
                ] = 0  # Important! Updated! CLONE mode.
                c4d.CallButton(tool, c4d.ID_CA_MIRROR_TOOL)
            doc.SetActiveObject(objActive)
            c4d.EventAdd()
            c4d.CallCommand(200000088)
        except:
            pass

    def getObjHeight(self, meshObj):
        pntPosList = meshObj.GetAllPoints()

        Xmin = 0
        Xmax = 0
        Ymin = 0
        Ymax = 0
        Zmin = 0
        Zmax = 0

        sumOfPositions = c4d.Vector(0, 0, 0)

        for pos in pntPosList:

            if pos[0] < Xmin:
                Xmin = pos[0]
            elif pos[0] > Xmax:
                Xmax = pos[0]
            if pos[1] < Ymin:
                Ymin = pos[1]
            elif pos[1] > Ymax:
                Ymax = pos[1]
            if pos[2] < Zmin:
                Zmin = pos[2]
            elif pos[2] > Zmax:
                Zmax = pos[2]

            sumOfPositions += pos

        sourceScaleY = meshObj[c4d.ID_BASEOBJECT_REL_SCALE, c4d.VECTOR_Y]
        sourcePosZ = meshObj.GetAbsPos()[2]
        sourcePosX = meshObj.GetAbsPos()[0]
        YmaxGlobal = (Ymax * sourceScaleY) + meshObj.GetAbsPos()[1]
        YminGlobal = (Ymin * sourceScaleY) + meshObj.GetAbsPos()[1]

        nullMasterSize = self.GetDistance(YminGlobal, YmaxGlobal)
        return nullMasterSize

    def fingerAngleLimit(self, obj):
        doc = documents.GetActiveDocument()
        try:
            jointAngle = obj[c4d.ID_BASEOBJECT_REL_ROTATION, c4d.VECTOR_X]
            if jointAngle > 0:
                obj[c4d.ID_BASEOBJECT_REL_ROTATION, c4d.VECTOR_X] = 0
                c4d.EventAdd()
        except:
            pass

    def setLiveSelectionTool(self):
        doc = documents.GetActiveDocument()
        c4d.CallCommand(12139)  # Points
        c4d.CallCommand(200000083)  # Live Selection
        tool = c4d.plugins.FindPlugin(doc.GetAction(), c4d.PLUGINTYPE_TOOL)
        tool[c4d.MDATA_SELECTLIVE_VISIBLE] = False
        c4d.EventAdd()

    def makeNull(self, nullName, target):
        doc = c4d.documents.GetActiveDocument()
        objNull = c4d.BaseObject(c4d.Onull)
        objNull.SetName(dazName + "_IKM-StartGuides")
        objNull.SetMg(target.GetMg())
        doc.InsertObject(objNull)
        c4d.EventAdd()

        return objNull

    def removeStuff(self):
        doc = documents.GetActiveDocument()
        answer = gui.MessageDialog(
            "Are you sure to remove Guides and RIG???\n\nYES:REMOVES ALL!!!",
            c4d.GEMB_YESNOCANCEL,
        )
        removed = 0
        if answer == 6:
            try:
                obj = doc.SearchObject(dazName + "_IKM-Guides")
                obj.Remove()
                c4d.EventAdd()
                removed = 1
            except:
                print("IKM: Can't delete")

        return removed

    def freezeChilds(self, parentObj=""):
        doc = c4d.documents.GetActiveDocument()
        obj = doc.SearchObject(parentObj)

        try:

            for x in self.iterateObjChilds(obj):
                # Transfer coords info to freeze info
                x.SetFrozenPos(x.GetAbsPos())
                x.SetFrozenRot(x.GetAbsRot())

                # Zero coords...
                x.SetRelPos(c4d.Vector(0, 0, 0))
                x.SetRelRot(c4d.Vector(0, 0, 0))

        except:
            pass

        c4d.EventAdd()

    def resetPRS(self, parentObj=""):
        doc = c4d.documents.GetActiveDocument()
        obj = parentObj

        if obj != None:
            for x in self.iterateObjChilds(obj):
                # Zero coords...
                x.SetRelPos(c4d.Vector(0, 0, 0))
                x.SetRelRot(c4d.Vector(0, 0, 0))
                x.SetRelScale(c4d.Vector(1, 1, 1))

        c4d.EventAdd()

    def freezePolygons(self, parentObj=""):
        doc = c4d.documents.GetActiveDocument()
        obj = doc.SearchObject(parentObj)

        bc = doc.GetData()  # Get the document's container
        sf = bc.GetLong(c4d.DOCUMENT_SELECTIONFILTER)  # Get the filter bit mask
        bc.SetLong(
            c4d.DOCUMENT_SELECTIONFILTER, 2
        )  # Use the Bit info to change the container in memory only
        doc.SetData(bc)  # Execute the changes made to the container from memory
        dzc4d.deselect_all()  # Deselect
        c4d.EventAdd()

    def CreateLayer(self, layername, layercolor):
        doc = c4d.documents.GetActiveDocument()
        root = doc.GetLayerObjectRoot()  # Gets the layer manager
        LayersList = root.GetChildren()  # Get Layer list
        # check if layer already exist
        layerexist = False
        for layers in LayersList:
            name = layers.GetName()
            if name == layername:
                layerexist = True
        # print "layerexist: ", layerexist
        if not layerexist:
            c4d.CallCommand(100004738)  # New Layer
            c4d.EventAdd()
            # rename new layer
            LayersList = (
                root.GetChildren()
            )  # redo getchildren, because a new one was added.
            for layers in LayersList:
                name = layers.GetName()
                if name == "Layer":
                    layers.SetName(layername)
                    layers.SetBit(c4d.BIT_ACTIVE)  # set layer active
                    layers[c4d.ID_LAYER_COLOR] = layercolor
                    c4d.EventAdd()
        return layers  # end createlayer

    def layerSettings(self, obj, lockValue=1, forceLock=0):
        doc = documents.GetActiveDocument()
        if obj == None:
            layer = self.getLayer("IKM_Lock")
            if layer == None:
                return 0
        else:
            layer = obj[c4d.ID_LAYER_LINK]

        if layer == None:
            layer = self.CreateLayer("IKM_Lock", c4d.Vector(255, 0, 0))  # Create layer
            color = layer[c4d.ID_LAYER_COLOR] = c4d.Vector(
                1, 0, 0
            )  # Sets layer color to black
            obj[c4d.ID_LAYER_LINK] = layer
        else:
            if layer.GetName() == "IKM_Lock":
                try:
                    layer.Remove()
                except:
                    print("Lock layer remove skipped...")

        layer_data = layer.GetLayerData(doc)
        lockValue = layer_data["locked"]

        if lockValue == True:
            layer_data["locked"] = False
            layer.SetLayerData(doc, layer_data)
            try:
                doc.SetActiveObject(obj, c4d.SELECTION_NEW)
            except:
                pass

        if forceLock == 1 or lockValue == False:
            layer_data["locked"] = True
            layer.SetLayerData(doc, layer_data)
            dzc4d.deselect_all()  # Deselect All

        c4d.EventAdd()

        return lockValue

    def resetObj(self, obj):
        doc = c4d.documents.GetActiveDocument()
        objOrigName = obj.GetName()
        tempNull = self.makeNull("tempNull", obj)
        tempNull.SetAbsRot(c4d.Vector(0))
        tempNull.SetAbsScale(c4d.Vector(1))
        tempNull.SetName("TempNull")
        dzc4d.deselect_all()  # Deselect All
        doc.SetActiveObject(tempNull, c4d.SELECTION_NEW)
        doc.SetActiveObject(obj, c4d.SELECTION_ADD)
        c4d.CallCommand(16768)  # Connect Objects + Delete
        fixedObj = doc.GetActiveObject()
        fixedObj.SetName(objOrigName)
        c4d.EventAdd()
        return fixedObj

    def hideGuides(self, visibility=1):
        doc = documents.GetActiveDocument()
        try:
            if dazName != None:
                guidesRoot = doc.SearchObject(dazName + "__IKM-Guides")
                guideNulls = ikmaxUtils().iterateObjChilds(guidesRoot)
                for obj in guideNulls:
                    obj()[c4d.ID_BASEOBJECT_VISIBILITY_RENDER] = visibility
                    obj()[c4d.ID_BASEOBJECT_VISIBILITY_EDITOR] = visibility
                guidesRoot()[c4d.ID_BASEOBJECT_VISIBILITY_RENDER] = visibility
                guidesRoot()[c4d.ID_BASEOBJECT_VISIBILITY_EDITOR] = visibility
                c4d.EventAdd()
        except:
            pass

    def removeIK(self):
        if dazName != None:
            doc = documents.GetActiveDocument()
            ikControls = doc.SearchObject(dazName + "IKM_Controls")
            jointsRoot = doc.SearchObject(dazName + rig_label("jPelvis"))
            tags = TagIterator(jointsRoot)
            try:
                ikControls.Remove()
            except:
                print("Can't remove IK")
            for tag in tags:
                tag.Remove()
            for x in ikmaxUtils().iterateObjChilds(jointsRoot):
                tags = TagIterator(x)
                for tag in tags:
                    tagType = tag.GetTypeName()
                    print(tagType)
                    tag.Remove()
            c4d.EventAdd()

    def removeSKIN(self, obj):
        if obj != None:
            doc = documents.GetActiveDocument()
            tags = TagIterator(obj)
            for tag in tags:
                if "Weight" in tag.GetName():
                    tag.Remove()
            try:
                if obj.GetDown().GetName() == "Skin":
                    obj.GetDown().Remove()
            except:
                pass
            c4d.EventAdd()

    def removeRIG(self):
        if dazName != None:
            doc = documents.GetActiveDocument()
            jointsRoot = doc.SearchObject(dazName + rig_label("jPelvis"))
            try:
                jointsRoot.Remove()
            except:
                print("Can't remove Rig")
            c4d.EventAdd()

    def removeMirrorGuides(self):
        guidesToMirror = [
            rig_label("Pinky_end"),
            rig_label("Pinky3"),
            rig_label("Pinky2"),
            rig_label("Pinky1"),
            rig_label("Ring_end"),
            rig_label("Ring3"),
            rig_label("Ring2"),
            rig_label("Ring1"),
            rig_label("Middle_end"),
            rig_label("Middle3"),
            rig_label("Middle2"),
            rig_label("Middle1"),
            rig_label("Index_end"),
            rig_label("Index3"),
            rig_label("Index2"),
            rig_label("Index1"),
            rig_label("Thumb_end"),
            rig_label("Thumb2"),
            rig_label("Thumb3"),
            rig_label("Thumb1"),
            rig_label("Hand"),
            rig_label("Elbow"),
            rig_label("Shoulder"),
            rig_label("Toes_end"),
            rig_label("Toes"),
            rig_label("Foot"),
            rig_label("Knee"),
            rig_label("LegUpper"),
        ]
        sideNameR = "___R"
        for g in guidesToMirror:
            ikmGenerator().removeObj(dazName + g + sideNameR)
        ikmGenerator().removeObj(dazName + rig_label("Collar") + sideNameR)
        ikmGenerator().removeObj(dazName + rig_label("Collar"))
        c4d.EventAdd()

    def removeRIGandMirrorsandGuides(self):
        try:
            ikmaxUtils().removeIK()
        except:
            pass
        ikmaxUtils().removeRIG()
        ikmaxUtils().hideGuides(0)
        try:
            ikmaxUtils().removeMirrorGuides()
        except:
            pass

    def finalFingersAlignamentPass(self, sidename=""):
        doc = documents.GetActiveDocument()
        jIndex1 = doc.SearchObject(dazName + rig_label("jIndex1") + sidename)
        jMiddle1 = doc.SearchObject(dazName + rig_label("jMiddle1") + sidename)
        jRing1 = doc.SearchObject(dazName + rig_label("jRing1") + sidename)
        jPink1 = doc.SearchObject(dazName + rig_label("jPink1") + sidename)

        fingersList = [
            rig_label("jIndex2"),
            rig_label("jIndex3"),
            rig_label("jMiddle2"),
            rig_label("jMiddle3"),
            rig_label("jRing2"),
            rig_label("jRing3"),
            rig_label("jPink2"),
            rig_label("jPink3"),
        ]

        def zeroYZ(obj):
            if obj.GetRelRot()[0] < 0.09 and obj.GetRelRot()[0] > -0.09:
                obj[c4d.ID_BASEOBJECT_REL_ROTATION, c4d.VECTOR_X] = 0
            if obj.GetRelRot()[1] < 0.09 and obj.GetRelRot()[1] > -0.09:
                obj[c4d.ID_BASEOBJECT_REL_ROTATION, c4d.VECTOR_Y] = 0
            if obj.GetRelRot()[2] < 0.09 and obj.GetRelRot()[1] > -0.09:
                obj[c4d.ID_BASEOBJECT_REL_ROTATION, c4d.VECTOR_Z] = 0

        ikmGenerator().AlignBoneChain(dazName + rig_label("jIndex1") + sidename, 2, 1, 0, 1)
        ikmGenerator().AlignBoneChain(dazName + rig_label("jMiddle1") + sidename, 2, 1, 0, 1)
        ikmGenerator().AlignBoneChain(dazName + rig_label("jRing1") + sidename, 2, 1, 0, 1)
        ikmGenerator().AlignBoneChain(dazName + rig_label("jPink1") + sidename, 2, 1, 0, 1)

        for jointName in fingersList:
            joint = doc.SearchObject(dazName + jointName + sidename)
            if joint != None:
                zeroYZ(joint)

    def extraFingerAlign(self):
        doc = documents.GetActiveDocument()

        def alignJoint(objName, sideName="", zeroRot=False):
            joint = doc.SearchObject(dazName + objName + sideName)
            joint[c4d.ID_CA_JOINT_OBJECT_BONE_AXIS] = 0
            doc.SetActiveObject(joint, c4d.SELECTION_NEW)
            c4d.CallCommand(1019883)  # Align

        alignJoint(rig_label("jIndex1"), "", True)
        alignJoint(rig_label("jIndex2"), "", True)
        alignJoint(rig_label("jIndex3"), "", True)
        alignJoint(rig_label("jIndex4"), "", True)
        alignJoint(rig_label("jMiddle1"), "", True)
        alignJoint(rig_label("jMiddle2"), "", True)
        alignJoint(rig_label("jMiddle3"), "", True)
        alignJoint(rig_label("jMiddle4"), "", True)
        alignJoint(rig_label("jRing1"), "", True)
        alignJoint(rig_label("jRing2"), "", True)
        alignJoint(rig_label("jRing3"), "", True)
        alignJoint(rig_label("jRing4"), "", True)
        alignJoint(rig_label("jPink1"), "", True)
        alignJoint(rig_label("jPink2"), "", True)
        alignJoint(rig_label("jPink3"), "", True)
        alignJoint(rig_label("jPink4"), "", True)

    def getLayer(self, layername):
        doc = c4d.documents.GetActiveDocument()
        root = doc.GetLayerObjectRoot()  # Gets the layer manager
        LayersList = root.GetChildren()
        for layers in LayersList:
            name = layers.GetName()
            if name == layername:
                return layers

    def checkIfExist(self, whatToSearch):
        doc = documents.GetActiveDocument()
        result = 0

        if whatToSearch == "IKcontrols":
            result = doc.SearchObject(dazName + "IKM_Controls")
        if whatToSearch == rig_label("jHead"):
            result = doc.SearchObject(dazName + rig_label("jHead"))

        if result != None:
            result = 1

        return result


class ikmGenerator:
    def GetGlobalPosition(self, obj):
        try:
            return obj.GetMg().off
        except:
            pass

    # Fingers Make JOINTS --- START ----------------------------------------------------

    def checkAlignMethod(self, fingerName, sideName=""):
        doc = c4d.documents.GetActiveDocument()
        try:

            bStart = doc.SearchObject(dazName + fingerName + "1" + sideName)
            b1 = doc.SearchObject(dazName + fingerName + "2" + sideName)
            b2 = doc.SearchObject(dazName + fingerName + "3" + sideName)
            bEnd = doc.SearchObject(dazName + fingerName + "_end" + sideName)

            bEndPosX = bEnd.GetAbsPos()[0]
            bEndPosY = bEnd.GetAbsPos()[1]

            b1PosX = b1.GetAbsPos()[0]
            b1PosY = b1.GetAbsPos()[1]

            b2PosX = b2.GetAbsPos()[0]
            b2PosY = b2.GetAbsPos()[1]

            bStartPosX = bStart.GetAbsPos()[0]
            bStartPosY = bStart.GetAbsPos()[1]

            totalX = (bStartPosX + b2PosX + b1PosX + bEndPosX) - (bStartPosX * 4)
            totalY = (bStartPosY + b2PosY + b1PosY + bEndPosY) - (bStartPosY * 4)

            if totalX < 0:
                totalX *= -1

            if totalY < 0:
                totalY *= -1

            if totalY > totalX:
                str(totalX) + "  " + str(totalY) + "  Winner: Y"
                return "Y"
            if totalY < totalX:
                str(totalX) + "  " + str(totalY) + "  Winner: X"
                return "X"
        except:
            print("checkAlign skiped...")

    def alignOnePoint(self, aligMethod, startPoint, endPoint, pointToAlign):
        doc = c4d.documents.GetActiveDocument()
        try:
            bStart = doc.SearchObject(startPoint)
            bEnd = doc.SearchObject(endPoint)
            b1 = doc.SearchObject(pointToAlign)

            bEndPosX = bEnd.GetAbsPos()[0]
            bEndPosY = bEnd.GetAbsPos()[1]
            bEndPosZ = bEnd.GetAbsPos()[2]

            b1PosX = b1.GetAbsPos()[0]
            b1PosY = b1.GetAbsPos()[1]
            b1PosZ = b1.GetAbsPos()[2]

            bStartPosX = bStart.GetAbsPos()[0]
            bStartPosY = bStart.GetAbsPos()[1]
            bStartPosZ = bStart.GetAbsPos()[2]

            if aligMethod == "X":
                b1PosAlignX = bEndPosX - (
                    (bEndPosY - b1PosY) * (bEndPosX - bStartPosX)
                ) / (bEndPosY - bStartPosY)
                b1.SetAbsPos(c4d.Vector(b1PosAlignX, b1PosY, b1PosZ))

            if aligMethod == "X2":
                b1PosAlignX = bEndPosX - (
                    (bEndPosZ - b1PosZ) * (bEndPosX - bStartPosX)
                ) / (bEndPosZ - bStartPosZ)
                b1.SetAbsPos(c4d.Vector(b1PosAlignX, b1PosY, b1PosZ))

            if aligMethod == "H":
                # Align Horizontal ---------

                b1PosAlignY = bEndPosY - (
                    (bEndPosX - b1PosX) * (bEndPosY - bStartPosY)
                ) / (bEndPosX - bStartPosX)
                b1.SetAbsPos(c4d.Vector(b1PosX, b1PosAlignY, b1PosZ))

            if aligMethod == "V":
                # Align Vertical ----------

                b1PosAlignZ = bEndPosZ - (
                    (bEndPosX - b1PosX) * (bEndPosZ - bStartPosZ)
                ) / (bEndPosX - bStartPosX)
                # b2PosAlignZ = bEndPosZ - ((bEndPosX - b2PosX)*(bEndPosZ - bStartPosZ))/(bEndPosX - bStartPosX)

                b1.SetAbsPos(c4d.Vector(b1PosX, b1PosY, b1PosAlignZ))
                # b2.SetAbsPos(c4d.Vector(b2PosX, b2PosY ,b2PosAlignZ))

            if aligMethod == "V2":
                # Align Vertical if Fingers Down... ----------

                b1PosAlignZ = bEndPosZ - (
                    (bEndPosY - b1PosY) * (bEndPosZ - bStartPosZ)
                ) / (bEndPosY - bStartPosY)
                # b2PosAlignZ = bEndPosZ - ((bEndPosY - b2PosY)*(bEndPosZ - bStartPosZ))/(bEndPosY - bStartPosY)

                b1.SetAbsPos(c4d.Vector(b1PosX, b1PosY, b1PosAlignZ))
                # b2.SetAbsPos(c4d.Vector(b2PosX, b2PosY ,b2PosAlignZ))
        except:
            print("Align M1 skipped...")

        c4d.EventAdd()

    def alignFingers(self, aligMethod, fingerName, sideName=""):
        doc = c4d.documents.GetActiveDocument()

        bStart = doc.SearchObject(dazName + fingerName + "1" + sideName)
        b1 = doc.SearchObject(dazName + fingerName + "2" + sideName)
        b2 = doc.SearchObject(dazName + fingerName + "3" + sideName)
        bEnd = doc.SearchObject(dazName + fingerName + "_end" + sideName)

        bEndPosX = bEnd.GetAbsPos()[0]
        bEndPosY = bEnd.GetAbsPos()[1]
        bEndPosZ = bEnd.GetAbsPos()[2]

        b1PosX = b1.GetAbsPos()[0]
        b1PosY = b1.GetAbsPos()[1]
        b1PosZ = b1.GetAbsPos()[2]

        b2PosX = b2.GetAbsPos()[0]
        b2PosY = b2.GetAbsPos()[1]
        b2PosZ = b2.GetAbsPos()[2]

        bStartPosX = bStart.GetAbsPos()[0]
        bStartPosY = bStart.GetAbsPos()[1]
        bStartPosZ = bStart.GetAbsPos()[2]

        if aligMethod == "H":
            # Align Horizontal ---------

            b1PosAlignY = bEndPosY - ((bEndPosX - b1PosX) * (bEndPosY - bStartPosY)) / (
                bEndPosX - bStartPosX
            )
            b2PosAlignY = bEndPosY - ((bEndPosX - b2PosX) * (bEndPosY - bStartPosY)) / (
                bEndPosX - bStartPosX
            )

            b1.SetAbsPos(c4d.Vector(b1PosX, b1PosAlignY, b1PosZ))
            b2.SetAbsPos(c4d.Vector(b2PosX, b2PosAlignY, b2PosZ))

        if aligMethod == "V":
            # Align Vertical ----------

            b1PosAlignZ = bEndPosZ - ((bEndPosX - b1PosX) * (bEndPosZ - bStartPosZ)) / (
                bEndPosX - bStartPosX
            )
            b2PosAlignZ = bEndPosZ - ((bEndPosX - b2PosX) * (bEndPosZ - bStartPosZ)) / (
                bEndPosX - bStartPosX
            )

            b1.SetAbsPos(c4d.Vector(b1PosX, b1PosY, b1PosAlignZ))
            b2.SetAbsPos(c4d.Vector(b2PosX, b2PosY, b2PosAlignZ))

        if aligMethod == "V2":
            # Align Vertical if Fingers Down... ----------

            b1PosAlignZ = bEndPosZ - ((bEndPosY - b1PosY) * (bEndPosZ - bStartPosZ)) / (
                bEndPosY - bStartPosY
            )
            b2PosAlignZ = bEndPosZ - ((bEndPosY - b2PosY) * (bEndPosZ - bStartPosZ)) / (
                bEndPosY - bStartPosY
            )

            b1.SetAbsPos(c4d.Vector(b1PosX, b1PosY, b1PosAlignZ))
            b2.SetAbsPos(c4d.Vector(b2PosX, b2PosY, b2PosAlignZ))

        c4d.EventAdd()

    def makeJoint(self, jointName, jointParentName, globalPosName):
        doc = documents.GetActiveDocument()
        try:
            obj = c4d.BaseObject(c4d.Ojoint)
            obj.SetName(dazName + jointName)
            obj[c4d.ID_CA_JOINT_OBJECT_BONE_DISPLAY] = 2
            obj[c4d.ID_BASEOBJECT_USECOLOR] = True
            obj[c4d.ID_BASEOBJECT_COLOR] = c4d.Vector(1, 0, 1)
            try:
                obj[c4d.ID_BASELIST_ICON_COLORIZE_MODE] = 2
                obj[c4d.ID_BASELIST_ICON_COLOR] = obj[c4d.ID_BASEOBJECT_COLOR]
            except:
                obj[c4d.ID_CA_JOINT_OBJECT_ICONCOL] = True
            obj[c4d.ID_BASEOBJECT_XRAY] = False
            doc.InsertObject(obj)  # Insert object in document
            if jointParentName != "":
                parent = doc.SearchObject(dazName + jointParentName)
                obj.InsertUnder(parent)
            if globalPosName != "":
                globalPos = doc.SearchObject(dazName + globalPosName)
                obj.SetMg(globalPos.GetMg())
        except Exception as e:
            print(e)
            print("Joint skipped...", jointName)

        c4d.EventAdd()  # Send global event message

    def fixAlignRotChilds(self, jointName):
        doc = documents.GetActiveDocument()
        obj = doc.SearchObject(jointName)
        obj[c4d.ID_BASEOBJECT_REL_ROTATION, c4d.VECTOR_X] = 0

    def protectJoints(self, jointName, protectPreset):
        doc = documents.GetActiveDocument()
        obj = doc.SearchObject(jointName)
        tagProtec = c4d.BaseTag(5629)  # Protection Tag

        if protectPreset == "preset1":
            tagProtec[c4d.PROTECTION_P_X] = True
            tagProtec[c4d.PROTECTION_P_Y] = False
            tagProtec[c4d.PROTECTION_P_Z] = False
            tagProtec[c4d.PROTECTION_S_X] = False
            tagProtec[c4d.PROTECTION_S_Y] = False
            tagProtec[c4d.PROTECTION_S_Z] = False
            tagProtec[c4d.PROTECTION_R_X] = True
            tagProtec[c4d.PROTECTION_R_Y] = False
            tagProtec[c4d.PROTECTION_R_Z] = True

        obj.InsertTag(tagProtec)
        c4d.EventAdd()

    def makeJointAndAlign(self, jointName, GuideName, sideName=""):
        doc = documents.GetActiveDocument()
        self.makeJoint(jointName + "1" + sideName, "", GuideName + "1" + sideName)
        self.makeJoint(
            jointName + "2" + sideName,
            jointName + "1" + sideName,
            GuideName + "2" + sideName,
        )
        self.makeJoint(
            jointName + "3" + sideName,
            jointName + "2" + sideName,
            GuideName + "3" + sideName,
        )
        self.makeJoint(
            jointName + "4" + sideName,
            jointName + "3" + sideName,
            GuideName + "_end" + sideName,
        )
        c4d.EventAdd()
        doc.SetActiveObject(doc.SearchObject(jointName + "1" + sideName))
        c4d.CallCommand(1019883)  # Align
        c4d.EventAdd()
        self.fixAlignRotChilds(dazName + jointName + "2" + sideName)
        self.fixAlignRotChilds(dazName + jointName + "3" + sideName)
        self.fixAlignRotChilds(dazName + jointName + "4" + sideName)
        c4d.EventAdd()

    # Fingers Make JOINTS --- END ----------------------------------------------------

    # Fingers JOINTS align stuff --- START ----------------------------------------------------

    def compareIfBetter(self, jStart, distanceTestResult, bEnd, jEnd, rotValue):
        jStartRot = jStart[c4d.ID_BASEOBJECT_REL_ROTATION, c4d.VECTOR_Z]
        jStart[c4d.ID_BASEOBJECT_REL_ROTATION, c4d.VECTOR_Z] = rotValue

        distanceTestNew = self.GetGlobalPosition(bEnd) - self.GetGlobalPosition(jEnd)
        distanceTestNewResult = (
            abs(distanceTestNew[0]) + abs(distanceTestNew[1]) + abs(distanceTestNew[2])
        )

        if distanceTestNewResult < distanceTestResult:
            winnerRot = jStart[c4d.ID_BASEOBJECT_REL_ROTATION, c4d.VECTOR_Z]
            jStart[c4d.ID_BASEOBJECT_REL_ROTATION, c4d.VECTOR_Z] = winnerRot
            c4d.EventAdd()
            return winnerRot
        else:
            jStart[c4d.ID_BASEOBJECT_REL_ROTATION, c4d.VECTOR_Z] = jStartRot
            return 0

    def compareAndRotate(self, jStartName, jEndName, bEndName):
        doc = c4d.documents.GetActiveDocument()
        try:
            jStart = doc.SearchObject(dazName + jStartName)
            jEnd = doc.SearchObject(dazName + jEndName)
            bEnd = doc.SearchObject(dazName + bEndName)
            objs = doc.GetActiveObjects(0)

            bEndPosX = self.GetGlobalPosition(bEnd)[0]
            bEndPosY = self.GetGlobalPosition(bEnd)[1]
            bEndPosZ = self.GetGlobalPosition(bEnd)[2]

            jEndPosX = self.GetGlobalPosition(jEnd)[0]
            jEndPosY = self.GetGlobalPosition(jEnd)[1]
            jEndPosZ = self.GetGlobalPosition(jEnd)[2]

            jStartRot = jStart[c4d.ID_BASEOBJECT_REL_ROTATION, c4d.VECTOR_Z]

            distanceTest = self.GetGlobalPosition(bEnd) - self.GetGlobalPosition(jEnd)
            distanceTestResult = (
                abs(distanceTest[0]) + abs(distanceTest[1]) + abs(distanceTest[2])
            )

            winnerRot = jStartRot

            rotValues = [
                1,
                0.9,
                0.8,
                0.7,
                0.6,
                0.5,
                0.4,
                0.3,
                0.2,
                0.1,
                0,
                -0.1,
                -0.2,
                -0.3,
                -0.4,
                -0.5,
                -0.6,
                -0.7,
                -0.8,
                -0.9,
                -1,
            ]
            for i in rotValues:
                self.compareIfBetter(jStart, distanceTestResult, bEnd, jEnd, i)
            c4d.EventAdd()
        except:
            pass

    # Fingers JOINTS align stuff --- END ----------------------------------------------------

    def axisOrder(self, jointName):
        doc = documents.GetActiveDocument()
        joint = doc.SearchObject(dazName + jointName)
        joint[c4d.ID_BASEOBJECT_ROTATION_ORDER] = 6  # Previous: 5

    def AlignBoneChain(
        self, rootBone, upAxis, primaryAxis=1, primaryDirection=0, upDirection=4
    ):
        doc = documents.GetActiveDocument()
        dzc4d.deselect_all()  # Deselect All
        joint = doc.SearchObject(rootBone)
        doc.SetActiveObject(joint, c4d.SELECTION_NEW)
        c4d.CallCommand(1021334, 1021334)
        c4d.CallCommand(1021334)  # Joint Align Tool
        tool = c4d.plugins.FindPlugin(doc.GetAction(), c4d.PLUGINTYPE_TOOL)
        if tool is not None:
            tool[c4d.ID_CA_JOINT_ALIGN_PRIMARY_AXIS] = primaryAxis
            tool[c4d.ID_CA_JOINT_ALIGN_PRIMARY_DIRECTION] = primaryDirection
            tool[c4d.ID_CA_JOINT_ALIGN_UP_AXIS] = upAxis
            tool[c4d.ID_CA_JOINT_ALIGN_UP_DIRECTION] = upDirection
            tool[c4d.ID_CA_JOINT_ALIGN_UP_FROMPREV] = True
            tool[c4d.ID_CA_JOINT_ALIGN_CHILDREN] = True
            c4d.CallButton(tool, c4d.ID_CA_JOINT_ALIGN)

        c4d.EventAdd()

    def makeFingersFull(self, sideName=""):
        # Freeze and Protect ....
        doc = c4d.documents.GetActiveDocument()



        oldJoints = doc.SearchObject(rig_label("jPink1") + sideName)
        try:
            oldJoints.Remove()
        except:
            pass

        c4d.CallCommand(100004748)  # Unfold All

        self.checkAlignMethod(rig_label("Index"))

        # Align Guides
        if self.checkAlignMethod(rig_label("Index"), sideName) == "Y":
            self.alignFingers("V2", rig_label("Index"), sideName)
        if self.checkAlignMethod(rig_label("Index"), sideName) == "X":
            self.alignFingers("V", rig_label("Index"), sideName)
        if self.checkAlignMethod(rig_label("Middle"), sideName) == "Y":
            self.alignFingers("V2", rig_label("Middle"), sideName)
        if self.checkAlignMethod(rig_label("Middle"), sideName) == "X":
            self.alignFingers("V", rig_label("Middle"), sideName)
        if self.checkAlignMethod(rig_label("Ring"), sideName) == "Y":
            self.alignFingers("V2", rig_label("Ring"), sideName)
        if self.checkAlignMethod(rig_label("Ring"), sideName) == "X":
            self.alignFingers("V", rig_label("Ring"), sideName)
        if self.checkAlignMethod(rig_label("Pinky"), sideName) == "Y":
            self.alignFingers("V2", rig_label("Pinky"), sideName)
        if self.checkAlignMethod(rig_label("Pinky"), sideName) == "X":
            self.alignFingers("V", rig_label("Pinky"), sideName)
        c4d.EventAdd()

        self.makeJoint(rig_label("jThumb1") + sideName, "", rig_label("Thumb1") + sideName)
        self.makeJoint(rig_label("jThumb2") + sideName, rig_label("jThumb1") + sideName, rig_label("Thumb2") + sideName)
        self.makeJoint(rig_label("jThumb3") + sideName, rig_label("jThumb2") + sideName, rig_label("Thumb3") + sideName)
        self.makeJoint(
            rig_label("jThumb_end") + sideName, rig_label("jThumb3") + sideName, rig_label("Thumb_end") + sideName
        )
        self.AlignBoneChain(dazName + rig_label("jThumb1") + sideName, 2)

        # Bones stuff...
        self.makeJointAndAlign(rig_label("jPink"), rig_label("Pinky"), sideName)
        self.makeJointAndAlign(rig_label("jRing"), rig_label("Ring"), sideName)
        self.makeJointAndAlign(rig_label("jMiddle"), rig_label("Middle"), sideName)
        self.makeJointAndAlign(rig_label("jIndex"), rig_label("Index"), sideName)

        self.AlignBoneChain(rig_label("jIndex1") + sideName, 1)
        self.AlignBoneChain(rig_label("jMiddle1") + sideName, 1)
        self.AlignBoneChain(rig_label("jRing1") + sideName, 1)
        self.AlignBoneChain(rig_label("jPink1") + sideName, 1)

        c4d.EventAdd()

        for i in range(0, 20):
            self.compareAndRotate(
                rig_label("jIndex1") + sideName, rig_label("jIndex4") + sideName, rig_label("Index_end") + sideName
            )
            self.compareAndRotate(
                rig_label("jMiddle1") + sideName, rig_label("jMiddle4") + sideName, rig_label("Middle_end") + sideName
            )
            self.compareAndRotate(
                rig_label("jRing1") + sideName, rig_label("jRing4") + sideName, rig_label("Ring_end") + sideName
            )
            self.compareAndRotate(
                rig_label("jPink1") + sideName, rig_label("jPink4") + sideName, rig_label("Pinky_end") + sideName
            )
            pass

        self.axisOrder(rig_label("jIndex1") + sideName)
        self.axisOrder(rig_label("jIndex2") + sideName)
        self.axisOrder(rig_label("jIndex3") + sideName)
        self.axisOrder(rig_label("jIndex4") + sideName)

        self.axisOrder(rig_label("jMiddle1") + sideName)
        self.axisOrder(rig_label("jMiddle2") + sideName)
        self.axisOrder(rig_label("jMiddle3") + sideName)
        self.axisOrder(rig_label("jMiddle4") + sideName)

        self.axisOrder(rig_label("jRing1") + sideName)
        self.axisOrder(rig_label("jRing2") + sideName)
        self.axisOrder(rig_label("jRing3") + sideName)
        self.axisOrder(rig_label("jRing4") + sideName)

        self.axisOrder(rig_label("jPink1") + sideName)
        self.axisOrder(rig_label("jPink2") + sideName)
        self.axisOrder(rig_label("jPink3") + sideName)
        self.axisOrder(rig_label("jPink4") + sideName)

    # Fingers Make JOINTS --- START ----------------------------------------------------

    # Fingers Make JOINTS --- END ----------------------------------------------------

    def makeNull(self, nullName, objPosition, preset):
        doc = documents.GetActiveDocument()
        obj = c4d.BaseObject(c4d.Onull)  # Create new cube
        obj.SetName(nullName)
        target = doc.SearchObject(objPosition)
        obj.SetMg(target.GetMg())
        doc.InsertObject(obj)

        mastersize = 220.0  # EXTRADialog.MASTERSIZE

        obj[c4d.NULLOBJECT_DISPLAY] = 11
        obj[c4d.NULLOBJECT_ORIENTATION] = 1
        obj[c4d.NULLOBJECT_RADIUS] = mastersize / 60
        obj[c4d.ID_BASEOBJECT_ROTATION_ORDER] = 5  # AXIS ORDER!!!!! NEW !
        if preset == "zeroRot":
            obj[c4d.ID_BASEOBJECT_REL_ROTATION, c4d.VECTOR_Z] = 0
        if preset == "zeroRotInvisible":
            obj[c4d.ID_BASEOBJECT_REL_ROTATION, c4d.VECTOR_Z] = 0
            obj[c4d.NULLOBJECT_DISPLAY] = 0
        if preset == "pelvis":
            obj[c4d.NULLOBJECT_DISPLAY] = 7
            obj[c4d.NULLOBJECT_ORIENTATION] = 3
            obj[c4d.NULLOBJECT_ASPECTRATIO] = 0.8
            obj[c4d.NULLOBJECT_RADIUS] = mastersize / 6
            obj[c4d.ID_BASEOBJECT_USECOLOR] = 2
            # obj[c4d.NULLOBJECT_ICONCOL] = True
            obj[c4d.ID_BASEOBJECT_COLOR] = c4d.Vector(0, 1, 0)
        if preset == "head":
            obj[c4d.NULLOBJECT_DISPLAY] = 2
            obj[c4d.NULLOBJECT_ORIENTATION] = 3
            obj[c4d.NULLOBJECT_ASPECTRATIO] = 1.3
            obj[c4d.NULLOBJECT_RADIUS] = mastersize / 16
            obj[c4d.ID_BASEOBJECT_USECOLOR] = 2
            # obj[c4d.NULLOBJECT_ICONCOL] = True
            obj[c4d.ID_BASEOBJECT_COLOR] = c4d.Vector(1, 1, 0)
        if preset == "neck":
            obj[c4d.NULLOBJECT_DISPLAY] = 2
            obj[c4d.NULLOBJECT_ORIENTATION] = 3
            obj[c4d.NULLOBJECT_ASPECTRATIO] = 1
            obj[c4d.NULLOBJECT_RADIUS] = mastersize / 16
            obj[c4d.ID_BASEOBJECT_USECOLOR] = 2
            # obj[c4d.NULLOBJECT_ICONCOL] = True
            obj[c4d.ID_BASEOBJECT_COLOR] = c4d.Vector(1, 0.7, 0)
        if preset == "spine":
            obj[c4d.NULLOBJECT_DISPLAY] = 7
            obj[c4d.NULLOBJECT_ORIENTATION] = 3
            obj[c4d.NULLOBJECT_ASPECTRATIO] = 0.8
            obj[c4d.NULLOBJECT_RADIUS] = mastersize / 10
            obj[c4d.ID_BASEOBJECT_USECOLOR] = 2
            # obj[c4d.NULLOBJECT_ICONCOL] = True
            obj[c4d.ID_BASEOBJECT_COLOR] = c4d.Vector(1, 0.7, 0)
        if preset == "ROOT":
            obj[c4d.NULLOBJECT_DISPLAY] = 7
            obj[c4d.NULLOBJECT_ORIENTATION] = 3
            # obj[c4d.NULLOBJECT_ASPECTRATIO] = 0.5
            obj[c4d.NULLOBJECT_RADIUS] = mastersize / 4
            obj[c4d.ID_BASEOBJECT_USECOLOR] = 2
            # obj[c4d.NULLOBJECT_ICONCOL] = True
            obj[c4d.ID_BASEOBJECT_COLOR] = c4d.Vector(1, 1, 0)
            obj[c4d.ID_BASEOBJECT_REL_POSITION, c4d.VECTOR_Y] = 0
        if preset == "pole":
            obj[c4d.NULLOBJECT_DISPLAY] = 13
            obj[c4d.NULLOBJECT_ORIENTATION] = 3
            # obj[c4d.NULLOBJECT_ASPECTRATIO] = 0.5
            obj[c4d.NULLOBJECT_RADIUS] = mastersize / 60
            obj[c4d.ID_BASEOBJECT_USECOLOR] = 2
            # obj[c4d.NULLOBJECT_ICONCOL] = True
            obj[c4d.ID_BASEOBJECT_COLOR] = c4d.Vector(1, 0, 0.5)
        if preset == "cube":
            obj[c4d.NULLOBJECT_DISPLAY] = 11
            obj[c4d.NULLOBJECT_ORIENTATION] = 3
            obj[c4d.NULLOBJECT_ASPECTRATIO] = 1
            obj[c4d.NULLOBJECT_RADIUS] = mastersize / 50
            obj[c4d.ID_BASEOBJECT_USECOLOR] = 2
            # obj[c4d.NULLOBJECT_ICONCOL] = True
            obj[c4d.ID_BASEOBJECT_COLOR] = c4d.Vector(0, 1, 1)
        if preset == "collar":
            obj[c4d.NULLOBJECT_DISPLAY] = 2
            obj[c4d.NULLOBJECT_ORIENTATION] = 2
            obj[c4d.NULLOBJECT_ASPECTRATIO] = 1
            obj[c4d.NULLOBJECT_RADIUS] = mastersize / 20 - 2
            obj[c4d.ID_BASEOBJECT_USECOLOR] = 2
            # obj[c4d.NULLOBJECT_ICONCOL] = True
            obj[c4d.ID_BASEOBJECT_COLOR] = c4d.Vector(0, 1, 1)
        if preset == "twist":
            obj[c4d.NULLOBJECT_DISPLAY] = 2
            obj[c4d.NULLOBJECT_ORIENTATION] = 2
            obj[c4d.NULLOBJECT_ASPECTRATIO] = 1
            obj[c4d.NULLOBJECT_RADIUS] = mastersize / 30
            obj[c4d.ID_BASEOBJECT_USECOLOR] = 2
            # obj[c4d.NULLOBJECT_ICONCOL] = True
            obj[c4d.ID_BASEOBJECT_COLOR] = c4d.Vector(0, 1, 1)
        if preset == "twist":
            obj[c4d.NULLOBJECT_DISPLAY] = 7
            obj[c4d.NULLOBJECT_ORIENTATION] = 2
            obj[c4d.NULLOBJECT_ASPECTRATIO] = 1
            obj[c4d.NULLOBJECT_RADIUS] = mastersize / 35
            obj[c4d.ID_BASEOBJECT_USECOLOR] = 2
            # obj[c4d.NULLOBJECT_ICONCOL] = True
            obj[c4d.ID_BASEOBJECT_COLOR] = c4d.Vector(0, 1, 1)
        if preset == "sphereToe":
            obj[c4d.NULLOBJECT_DISPLAY] = 13
            obj[c4d.NULLOBJECT_ORIENTATION] = 3
            # obj[c4d.NULLOBJECT_ASPECTRATIO] = 0.5
            obj[c4d.NULLOBJECT_RADIUS] = mastersize / 40
            obj[c4d.ID_BASEOBJECT_USECOLOR] = 2
            # obj[c4d.NULLOBJECT_ICONCOL] = True
            obj[c4d.ID_BASEOBJECT_COLOR] = c4d.Vector(0, 1, 1)
        if preset == rig_label("Foot_Platform"):
            obj[c4d.ID_BASEOBJECT_REL_POSITION, c4d.VECTOR_Y] = 0
            obj[c4d.NULLOBJECT_DISPLAY] = 14
            obj[c4d.NULLOBJECT_ORIENTATION] = 3
            obj[c4d.NULLOBJECT_ASPECTRATIO] = 0.5
            obj[c4d.NULLOBJECT_RADIUS] = mastersize / 10
            obj[c4d.ID_BASEOBJECT_USECOLOR] = 2
            # obj[c4d.NULLOBJECT_ICONCOL] = True
            obj[c4d.ID_BASEOBJECT_COLOR] = c4d.Vector(1, 1, 0)
        if preset == rig_label("Foot_PlatformNEW"):
            obj[c4d.ID_BASEOBJECT_REL_ROTATION, c4d.VECTOR_X] = 0
            obj[c4d.ID_BASEOBJECT_REL_ROTATION, c4d.VECTOR_Y] = 0
            obj[c4d.ID_BASEOBJECT_REL_ROTATION, c4d.VECTOR_Z] = 0
            obj[c4d.NULLOBJECT_DISPLAY] = 2
            obj[c4d.NULLOBJECT_ORIENTATION] = 3
            obj[c4d.NULLOBJECT_ASPECTRATIO] = 1
            obj[c4d.NULLOBJECT_RADIUS] = mastersize / 25
            obj[c4d.ID_BASEOBJECT_USECOLOR] = 2
            # obj[c4d.NULLOBJECT_ICONCOL] = True
            obj[c4d.ID_BASEOBJECT_COLOR] = c4d.Vector(1, 1, 0)

        obj[c4d.ID_BASEOBJECT_VISIBILITY_EDITOR] = 0
        if preset == "none":
            obj[c4d.NULLOBJECT_DISPLAY] = 0

        return obj

    def makeIKtag(
        self,
        jName,
        jTarget,
        goalName,
        poleName="",
        polePosition="",
        poleDirection="",
        preset="",
    ):
        doc = documents.GetActiveDocument()
        print("building IK tag for jName '"+jName+"' jTarget '"+jTarget+ "' goal '"+goalName+"' pole '"+poleName+"' polePosition '"+polePosition+"' poleDirection '"+poleDirection+"' preset '"+preset)
        ikJoint = doc.SearchObject(dazName + jName)
        ikJointTarget = doc.SearchObject(dazName + jTarget)
        nullGoal = doc.SearchObject(dazName + goalName)

        IKTag = c4d.BaseTag(1019561)  # IK Tag

        ikJoint.InsertTag(IKTag)
        IKTag[c4d.ID_CA_IK_TAG_TIP] = ikJointTarget
        IKTag[c4d.ID_CA_IK_TAG_TARGET] = nullGoal
        IKTag[c4d.ID_CA_IK_TAG_DRAW_HANDLE_LINE] = False

        MASTERSIZE = 220.0
        if poleName != "":
            self.makeNull(dazName + poleName, dazName + polePosition, "pole")  # Pole
            poleGoal = doc.SearchObject(dazName + poleName)
            # POLE ZERO ROTATION
            poleGoal[c4d.ID_BASEOBJECT_REL_ROTATION, c4d.VECTOR_X] = 0
            poleGoal[c4d.ID_BASEOBJECT_REL_ROTATION, c4d.VECTOR_Y] = 0
            poleGoal[c4d.ID_BASEOBJECT_REL_ROTATION, c4d.VECTOR_Z] = 0

            if poleDirection == "":
                poleGoal[c4d.ID_BASEOBJECT_REL_POSITION, c4d.VECTOR_Z] += MASTERSIZE / 4
                pass
            if poleDirection == "Negative":
                poleGoal[c4d.ID_BASEOBJECT_REL_POSITION, c4d.VECTOR_Z] -= MASTERSIZE / 4
                pass
            IKTag[c4d.ID_CA_IK_TAG_POLE] = poleGoal

        if rig_label("Hand") in jTarget:
            IKTag[c4d.ID_CA_IK_TAG_GOAL_CONSTRAIN] = True
            pass

        c4d.EventAdd()

    def constraintObj(self, slave, master, mode="", searchObj=1):
        print("building constraint for slave '"+slave+"' master '"+master+ "' mode '"+mode+"'")

        doc = documents.GetActiveDocument()
        if searchObj == 1:
            slaveObj = doc.SearchObject(slave)
            masterObj = doc.SearchObject(master)
        else:
            slaveObj = slave
            masterObj = master
        mg = slaveObj.GetMg()

        constraintTAG = c4d.BaseTag(1019364)
        if mode == "":
            constraintTAG[c4d.ID_CA_CONSTRAINT_TAG_PSR] = True
            constraintTAG[10001] = masterObj
        if mode == "UPVECTOR":
            constraintTAG[c4d.ID_CA_CONSTRAINT_TAG_UP] = True
            constraintTAG[40004] = 0
            constraintTAG[40005] = 5
            constraintTAG[c4d.ID_CA_CONSTRAINT_TAG_UP_MAINTAIN] = True
            # c4d.gui.MessageDialog(masterObj.GetName())
            constraintTAG[40001] = masterObj

        if mode == "ROTATION":
            constraintTAG[c4d.ID_CA_CONSTRAINT_TAG_PSR] = True
            constraintTAG[10005] = False
            constraintTAG[10006] = False
            constraintTAG[10001] = masterObj
        if mode == "AIM":
            constraintTAG[c4d.ID_CA_CONSTRAINT_TAG_AIM] = True
            constraintTAG[c4d.ID_CA_CONSTRAINT_TAG_AIM_MAINTAIN] = True
            constraintTAG[20001] = masterObj
        if mode == "PARENT":
            nullSlave = c4d.BaseObject(c4d.Onull)
            nullSlave.SetName("nullSlave")
            nullSlave.SetMg(slaveObj.GetMg())
            doc.InsertObject(nullSlave)
            nullParent = c4d.BaseObject(c4d.Onull)
            nullParent.SetName("nullParent")
            nullParent.SetMg(masterObj.GetMg())
            slaveMg = nullSlave.GetMg()
            doc.InsertObject(nullParent)
            nullSlave.InsertUnder(nullParent)
            nullSlave.SetMg(slaveMg)
            constraintTAG[c4d.EXPRESSION_ENABLE] = True
            constraintTAG[c4d.ID_CA_CONSTRAINT_TAG_PARENT_MAINTAIN] = False
            constraintTAG[c4d.ID_CA_CONSTRAINT_TAG_PARENT_FROZEN] = False
            constraintTAG[c4d.ID_CA_CONSTRAINT_TAG_PARENT] = True
            constraintTAG[30001] = masterObj
            constraintTAG[30009, 1000] = c4d.Vector(
                nullSlave.GetRelPos()[0],
                nullSlave.GetRelPos()[1],
                nullSlave.GetRelPos()[2],
            )
            constraintTAG[30009, 1002] = c4d.Vector(
                nullSlave.GetRelRot()[0],
                nullSlave.GetRelRot()[1],
                nullSlave.GetRelRot()[2],
            )

            PriorityDataInitial = c4d.PriorityData()
            PriorityDataInitial.SetPriorityValue(
                c4d.PRIORITYVALUE_MODE, c4d.CYCLE_GENERATORS
            )
            PriorityDataInitial.SetPriorityValue(c4d.PRIORITYVALUE_PRIORITY, 0)
            PriorityDataInitial.SetPriorityValue(c4d.PRIORITYVALUE_CAMERADEPENDENT, 0)
            constraintTAG[c4d.EXPRESSION_PRIORITY] = PriorityDataInitial
            try:
                nullParent.Remove()
            except:
                pass
        slaveObj.InsertTag(constraintTAG)

        c4d.EventAdd()

    def makeChildKeepPos(self, childName, parentName):
        doc = documents.GetActiveDocument()
        try:
            child = doc.SearchObject(childName)
            parent = doc.SearchObject(parentName)
            mg = child.GetMg()
            child.InsertUnder(parent)
            child.SetMg(mg)
        except:
            pass

    def removeObj(self, objName):
        doc = documents.GetActiveDocument()
        try:
            joint = doc.SearchObject(objName)
            joint.Remove()
        except:
            pass

    def makeCollarNull(self, sideName=""):
        doc = c4d.documents.GetActiveDocument()
        objNull = c4d.BaseObject(c4d.Onull)
        neck = doc.SearchObject(dazName + rig_label("Neck_Start"))
        ikmGuides = doc.SearchObject(dazName + "_IKM-Guides")
        shoulder = doc.SearchObject(dazName + rig_label("Shoulder") + sideName)

        objNull.SetName(dazName + rig_label("Collar") + sideName)
        objNull.InsertUnder(ikmGuides)
        objNull.SetMg(neck.GetMg())

        shoulderX = shoulder.GetRelPos()[0]
        shoulderY = shoulder.GetRelPos()[1]
        shoulderZ = shoulder.GetRelPos()[2]
        neckX = neck.GetRelPos()[0]
        neckY = neck.GetRelPos()[1]
        neckZ = neck.GetRelPos()[2]

        objNull.SetRelPos(c4d.Vector(((shoulderX - neckX) / 3), shoulderY, neckZ))

        c4d.EventAdd()

    def makeDAZCollarNull(self, sideName=""):
        doc = c4d.documents.GetActiveDocument()
        objNull = c4d.BaseObject(c4d.Onull)
        dazCollar = doc.SearchObject(rig_label("lCollar"))
        ikmGuides = doc.SearchObject(dazName + "_IKM-Guides")
        shoulder = doc.SearchObject(dazName + rig_label("Shoulder") + sideName)

        objNull.SetName(dazName + rig_label("Collar") + sideName)
        objNull.InsertUnder(ikmGuides)
        objNull.SetMg(dazCollar.GetMg())

        c4d.EventAdd()

    def mirrorNulls(self, nullName, addToName, parentName):
        doc = documents.GetActiveDocument()
        try:
            sourceNull = doc.SearchObject(nullName)

            self.makeNull(nullName + addToName, nullName, "")
            newNull = doc.SearchObject(nullName + addToName)

            self.makeChildKeepPos(nullName + addToName, parentName)
            newNull[c4d.ID_BASEOBJECT_REL_POSITION, c4d.VECTOR_X] *= -1
            newNull[c4d.NULLOBJECT_DISPLAY] = sourceNull[c4d.NULLOBJECT_DISPLAY]
            newNull[c4d.NULLOBJECT_RADIUS] = sourceNull[c4d.NULLOBJECT_RADIUS]
            newNull[c4d.NULLOBJECT_ASPECTRATIO] = sourceNull[c4d.NULLOBJECT_ASPECTRATIO]
            newNull[c4d.NULLOBJECT_ORIENTATION] = sourceNull[c4d.NULLOBJECT_ORIENTATION]
            newNull[c4d.ID_BASEOBJECT_COLOR] = sourceNull[c4d.ID_BASEOBJECT_COLOR]
            newNull[c4d.ID_BASEOBJECT_USECOLOR] = sourceNull[c4d.ID_BASEOBJECT_USECOLOR]
            try:
                newNull[c4d.ID_BASELIST_ICON_COLORIZE_MODE] = 2
                newNull[c4d.ID_BASELIST_ICON_COLOR] = newNull[c4d.ID_BASEOBJECT_COLOR]
            except:
                newNull[c4d.NULLOBJECT_ICONCOL] = sourceNull[c4d.NULLOBJECT_ICONCOL]
        except:
            print("skip mirrorNulls", nullName)

    def generateRig(self, sideName=""):
        doc = documents.GetActiveDocument()

        # --- ARM  ---------------------------------------------
        self.makeJoint(rig_label("jCollar") + sideName, rig_label("jChestUpper"), rig_label("Collar") + sideName)
        dazJoint = doc.SearchObject(rig_label("lCollar"))
        joint = doc.SearchObject(dazName + rig_label("jCollar") + sideName)

        try:
            joint.SetMg(dazJoint.GetMg())
        except:
            print("joint skip")
            pass
        try:
            self.makeJoint(
                rig_label("jArm") + sideName, rig_label("jCollar") + sideName, rig_label("Shoulder") + sideName
            )
        except:
            print("joint skip")
            pass
        self.makeJoint(rig_label("jForeArm") + sideName, rig_label("jArm") + sideName, rig_label("Elbow") + sideName)
        self.makeJoint(rig_label("jHand") + sideName, rig_label("jForeArm") + sideName, rig_label("Hand") + sideName)

        c4d.EventAdd()

        # ARM - Bones - Align
        joint = doc.SearchObject(dazName + rig_label("jArm") + sideName)
        doc.SetActiveObject(joint)
        c4d.CallCommand(1019883)  # Align

        # ARM - Bones - Align
        jFootBone = doc.SearchObject(dazName + rig_label("jArm") + sideName)
        jFootBone[c4d.ID_CA_JOINT_OBJECT_BONE_AXIS] = 0
        doc.SetActiveObject(jFootBone)
        c4d.CallCommand(1019883)  # Align
        jFootBone = doc.SearchObject(dazName + rig_label("jForeArm") + sideName)
        jFootBone[c4d.ID_CA_JOINT_OBJECT_BONE_AXIS] = 0
        doc.SetActiveObject(jFootBone)
        c4d.CallCommand(1019883)  # Align
        jFootBone = doc.SearchObject(dazName + rig_label("jHand") + sideName)
        jFootBone[c4d.ID_CA_JOINT_OBJECT_BONE_AXIS] = 0
        doc.SetActiveObject(jFootBone)
        c4d.CallCommand(1019883)  # Align
        # -------------------------------------------------

        # --- LEG ---------
        # LEG - Guides - Align
        self.alignOnePoint(
            "X",
            dazName + rig_label("LegUpper") + sideName,
            dazName + rig_label("Foot") + sideName,
            dazName + rig_label("Knee") + sideName,
        )
        c4d.EventAdd()
        # LEG - Bones - Create
        self.makeJoint(rig_label("jUpLeg") + sideName, rig_label("jPelvis"), rig_label("LegUpper") + sideName)
        self.makeJoint(rig_label("jLeg") + sideName, rig_label("jUpLeg") + sideName, rig_label("Knee") + sideName)

        self.AlignBoneChain(dazName + rig_label("jUpLeg") + sideName, 2)

        self.makeJoint(rig_label("jFoot") + sideName, rig_label("jLeg") + sideName, rig_label("Foot") + sideName)

        # LEG - Bones - Align
        jLegBone = doc.SearchObject(dazName + rig_label("jUpLeg") + sideName)
        doc.SetActiveObject(jLegBone)
        c4d.CallCommand(1019883)  # Align
        jLegBone = doc.SearchObject(dazName + rig_label("jLeg") + sideName)
        doc.SetActiveObject(jLegBone)
        c4d.CallCommand(1019883)  # Align

        # --- FOOT ---------
        # FOOT - Guides - Fix
        gToes = doc.SearchObject(dazName + rig_label("Toes") + sideName)
        gToesEnd = doc.SearchObject(dazName + rig_label("Toes_end") + sideName)
        if gToesEnd:
            gToesY = gToes.GetAbsPos()[1]
            gToesEndX = gToesEnd.GetAbsPos()[0]
            gToesEndY = gToesEnd.GetAbsPos()[1]
            gToesEndZ = gToesEnd.GetAbsPos()[2]
            gToesEnd.SetAbsPos(c4d.Vector(gToesEndX, gToesY, gToesEndZ))

        # FOOT - Guides - Align
        self.alignOnePoint(
            "X2",
            dazName + rig_label("Foot") + sideName,
            dazName + rig_label("Toes_end") + sideName,
            dazName + rig_label("Toes") + sideName,
        )
        c4d.EventAdd()
        # FOOT - Bones - Create
        self.makeJoint(rig_label("jFoot2") + sideName, "", rig_label("Foot") + sideName)
        self.makeJoint(rig_label("jToes") + sideName, rig_label("jFoot2") + sideName, rig_label("Toes") + sideName)
        self.makeJoint(
            rig_label("jToes_end") + sideName, rig_label("jToes") + sideName, rig_label("Toes_end") + sideName
        )

        self.removeObj(dazName + rig_label("jFoot") + sideName)

        jLegBone = doc.SearchObject(dazName + rig_label("jLeg") + sideName)
        jFootBone = doc.SearchObject(dazName + rig_label("jFoot2") + sideName)
        mg = jFootBone.GetMg()
        jFootBone.InsertUnder(jLegBone)
        jFootBone.SetMg(mg)
        jFootBone.SetName(dazName + rig_label("jFoot") + sideName)

        self.AlignBoneChain(dazName + rig_label("jUpLeg") + sideName, 2)
        self.AlignBoneChain(dazName + rig_label("jFoot") + sideName, 1, 0, 0, 1)

    def mirrorGuides(self, guides_to_mirror):
        daz_name = Utilities.get_daz_name() + "_"
        parentMirrorName = daz_name + "_IKM-Guides"
        addToName = "___R"
        for g in guides_to_mirror:
            print("mirroring "+daz_name+g+" with "+addToName+" into "+parentMirrorName)
            try:
                self.mirrorNulls(daz_name + g, addToName, parentMirrorName)
            except:
                print("skip mirror guide", g)

    def removeIfZero(self, objName):
        doc = documents.GetActiveDocument()
        obj = doc.SearchObject(objName)
        if obj.GetAbsPos() == c4d.Vector(0, 0, 0):
            obj.Remove()

    def checkFingersAmount(self, modelBase):
        def fingerExist(modelBase, jointName):
            doc = documents.GetActiveDocument()

            joint1 = doc.SearchObject(modelBase + jointName + "1")
            joint2 = doc.SearchObject(modelBase + jointName + "2")
            joint3 = doc.SearchObject(modelBase + jointName + "3")
            joint4 = doc.SearchObject(modelBase + jointName + "4")
            jointThumbEnd = doc.SearchObject(modelBase + jointName + "_end")
            complete = 1
            if rig_label("Thumb") in jointName:
                if joint1 != None and joint2 != None and jointThumbEnd != None:
                    pass
                else:
                    complete = 0
            else:
                if (
                    joint1 != None
                    and joint2 != None
                    and joint3 != None
                    and joint4 != None
                ):
                    pass
                else:
                    complete = 0

            return complete

        lastFinger = ""

        if fingerExist(modelBase, rig_label("jThumb")) == 1:
            lastFinger = rig_label("jThumb")
            if fingerExist(modelBase, rig_label("jIndex")) == 1:
                lastFinger = rig_label("jIndex")
                if fingerExist(modelBase, rig_label("jMiddle")) == 1:
                    lastFinger = rig_label("jMiddle")
                    if fingerExist(modelBase, rig_label("jRing")) == 1:
                        lastFinger = rig_label("jRing")
                        if fingerExist(modelBase, rig_label("jPinky")) == 1:
                            lastFinger = rig_label("jPinky")

        return lastFinger

    def makeRig(self):
        doc = documents.GetActiveDocument()
        guides_to_mirror = database().guides_to_mirror #_genesis9 if g9() else Database.guides_to_mirror
        center_joints = database().center_joints #_genesis9 if g9() else Database.center_joints
        sideName = "___R"

        # --- CENTER BONES -------------------------------------

        for joints in center_joints:
            self.makeJoint(joints[0], joints[1], joints[2])

        self.mirrorGuides(guides_to_mirror)

        self.generateRig()
        self.generateRig(sideName)

        self.makeFingersFull(sideName)
        self.makeFingersFull()

        jIndex1 = rig_label("jIndex1")
        jMiddle1 = rig_label("jMiddle1")
        jRing1 = rig_label("jRing1")
        jPink1 = rig_label("jPink1")
        jThumb1 = rig_label("jThumb1")
        jHand = rig_label("jHand")


        self.removeIfZero(dazName + jIndex1)
        self.removeIfZero(dazName + jMiddle1)
        self.removeIfZero(dazName + jRing1)
        self.removeIfZero(dazName + jPink1)
        self.removeIfZero(dazName + jThumb1)

        self.removeIfZero(dazName + jIndex1 + sideName)
        self.removeIfZero(dazName + jMiddle1 + sideName)
        self.removeIfZero(dazName + jRing1 + sideName)
        self.removeIfZero(dazName + jPink1 + sideName)
        self.removeIfZero(dazName + jThumb1 + sideName)

        self.makeChildKeepPos(
            dazName + jIndex1 + sideName, dazName + jHand + sideName
        )
        self.makeChildKeepPos(
            dazName + jMiddle1 + sideName, dazName + jHand + sideName
        )
        self.makeChildKeepPos(
            dazName + jRing1 + sideName, dazName + jHand + sideName
        )
        self.makeChildKeepPos(
            dazName + jPink1 + sideName, dazName + jHand + sideName
        )
        self.makeChildKeepPos(
            dazName + jThumb1 + sideName, dazName + jHand + sideName
        )

        self.makeChildKeepPos(dazName + jIndex1, dazName + jHand)
        self.makeChildKeepPos(dazName + jMiddle1, dazName + jHand)
        self.makeChildKeepPos(dazName + jRing1, dazName + jHand)
        self.makeChildKeepPos(dazName + jPink1, dazName + jHand)
        self.makeChildKeepPos(dazName + jThumb1, dazName + jHand)
        c4d.CallCommand(100004749)  # Fold All

        for g in guides_to_mirror:
            self.removeObj(g + sideName)

        # ALIGN FINGERS AND MIRROR RESULT
        lastFinger = self.checkFingersAmount(dazName)
        if lastFinger == rig_label("jMiddle") or lastFinger == rig_label("jRing") or lastFinger == rig_label("jPink"):
            alignFingersFull().start(dazName, lastFinger)
            objArm = doc.SearchObject(dazName + rig_label("jCollar"))
            suffix = "___R"
            ikmaxUtils().mirrorObjects(objArm, suffix)
        # ----

        ikmaxUtils().removeMirrorGuides()
        ikmaxUtils().hideGuides(1)

        c4d.EventAdd()

    def makeIKcontrols(self, sideName=""):
        doc = documents.GetActiveDocument()
        self.makeNull(
            dazName + rig_label("IK_Foot") + sideName,
            dazName + rig_label("jFoot") + sideName,
            "zeroRotInvisible",
        )
        self.makeNull(
            dazName + rig_label("Toe_Rot") + sideName, dazName + rig_label("jToes") + sideName, "sphereToe"
        )
        JointFixes.update_rotation_order(
            dazName + rig_label("Toe_Rot") + sideName, dazName + rig_label("jToes")
        )
        self.makeNull(
            dazName + rig_label("Foot_Roll") + sideName, dazName + rig_label("jToes") + sideName, "cube"
        )
        JointFixes.update_rotation_order(
            dazName + rig_label("Foot_Roll") + sideName, dazName + rig_label("jToes")
        )
        self.makeNull(
            dazName + rig_label("IK_Hand") + sideName, dazName + rig_label("jHand") + sideName, "cube"
        )
        JointFixes.update_rotation_order(
            dazName + rig_label("IK_Hand") + sideName, dazName + rig_label("jHand") + sideName
        )
        # Extra Controls
        self.makeNull(dazName + rig_label("Collar_ctrl"), dazName + rig_label("jCollar"), rig_label("collar"))
        JointFixes.update_rotation_order(dazName + rig_label("Collar_ctrl"), dazName + rig_label("jCollar"))
        self.constraintObj(dazName + rig_label("jCollar"), dazName + rig_label("Collar_ctrl"))

        self.makeIKtag(
            rig_label("jArm") + sideName,
            rig_label("jHand") + sideName,
            rig_label("IK_Hand") + sideName,
            rig_label("jArm.Pole")+ sideName,
            rig_label("Shoulder")+ sideName,
        )

        self.makeIKtag(
            rig_label("jUpLeg") + sideName,
            rig_label("jFoot") + sideName,
            rig_label("IK_Foot") + sideName,
            rig_label("jUpLeg.Pole") + sideName,
            rig_label("LegUpper") + sideName,
            "Negative",
        )

        self.makeNull(
            dazName + rig_label("Foot_Platform") + sideName,
            dazName + rig_label("IK_Foot") + sideName,
            rig_label("Foot_Platform"),
        )
        JointFixes.update_rotation_order(
            dazName + rig_label("Foot_Platform") + sideName, dazName + rig_label("IK_Foot") + sideName
        )
        self.makeChildKeepPos(
            dazName + rig_label("IK_Foot") + sideName, dazName + rig_label("Foot_Platform") + sideName
        )

        self.constraintObj(
            dazName + rig_label("jFoot") + sideName,
            dazName + rig_label("Foot_Platform") + sideName,
            "UPVECTOR",
        )
        self.constraintObj(
            dazName + rig_label("jHand") + sideName, dazName + rig_label("IK_Hand") + sideName, "ROTATION"
        )

        self.makeNull(
            dazName + rig_label("ToesEnd") + sideName, dazName + rig_label("jToes_end") + sideName, "none"
        )
        JointFixes.update_rotation_order(
            dazName + rig_label("ToesEnd") + sideName, dazName + rig_label("jToes_end") + sideName
        )
        self.makeIKtag(rig_label("jFoot") + sideName, rig_label("jToes") + sideName, rig_label("Toe_Rot") + sideName)
        self.makeIKtag(rig_label("jToes") + sideName, rig_label("jToes_end") + sideName, rig_label("ToesEnd") + sideName)

        self.makeChildKeepPos(
            dazName + rig_label("ToesEnd") + sideName, dazName + rig_label("Toe_Rot") + sideName
        )
        self.makeChildKeepPos(
            dazName + rig_label("Toe_Rot") + sideName, dazName + rig_label("Foot_Platform") + sideName
        )
        self.makeChildKeepPos(
            dazName + rig_label("Foot_Roll") + sideName, dazName + rig_label("Foot_Platform") + sideName
        )

        self.makeChildKeepPos(
            dazName + rig_label("IK_Foot") + sideName, dazName + rig_label("Foot_Roll") + sideName
        )

        if sideName == "":
            self.makeNull(dazName + rig_label("Pelvis_ctrl"), dazName + rig_label("jPelvis"), "pelvis")
            self.constraintObj(dazName + rig_label("jPelvis"), dazName + rig_label("Pelvis_ctrl"))

            # check if twistbones:
            self.makeNull(dazName + rig_label("ForearmTwist_ctrl"), rig_label("lForearmTwist"), "twist")
            self.makeNull(
                dazName + rig_label("ForearmTwist_ctrl___R"), rig_label("rForearmTwist"), "twist"
            ) 
        if sideName == "":
            self.makeNull(dazName + rig_label("Spine_ctrl"), dazName + rig_label("jSpine"), "spine")
            self.constraintObj(dazName + rig_label("jSpine"), dazName + rig_label("Spine_ctrl"))

        if sideName == "":  # Extra Controls
            newNull = self.makeNull(
                dazName + rig_label("AbdomenUpper_ctrl"), dazName + rig_label("jAbdomenUpper"), "spine"
            )
            JointFixes.update_rotation_order(
                dazName + rig_label("AbdomenUpper_ctrl"), dazName + rig_label("jAbdomenUpper")
            )
            self.constraintObj(dazName + rig_label("jAbdomenUpper"), dazName + rig_label("AbdomenUpper_ctrl"))
            newNull[c4d.ID_BASEOBJECT_VISIBILITY_EDITOR] = 1

            newNull = self.makeNull(
                dazName + rig_label("ChestUpper_ctrl"), dazName + rig_label("jChestUpper"), "spine"
            )
            self.constraintObj(dazName + rig_label("jChestUpper"), dazName + rig_label("ChestUpper_ctrl"))
            newNull[c4d.ID_BASEOBJECT_VISIBILITY_EDITOR] = 1

            self.makeNull(
                dazName + rig_label("Foot_PlatformBase") + sideName,
                dazName + rig_label("jFoot"),
                rig_label("Foot_PlatformNEW"),
            )
            self.makeNull(
                dazName + rig_label("Foot_PlatformBase___R") + sideName,
                dazName + rig_label("jFoot___R"),
                rig_label("Foot_PlatformNEW"),
            )
        if sideName == "":
            self.makeNull(dazName + rig_label("Chest_ctrl"), dazName + rig_label("jChest"), "spine")
            self.constraintObj(dazName + rig_label("jChest"), dazName + rig_label("Chest_ctrl"))

        if sideName == "":
            self.makeNull(dazName + rig_label("Neck_ctrl"), dazName + rig_label("jNeck"), "neck")
            self.constraintObj(dazName + rig_label("jNeck"), dazName + rig_label("Neck_ctrl"))

        if sideName == "":
            self.makeNull(dazName + rig_label("Head_ctrl"), dazName + rig_label("jHead"), "head")
            self.constraintObj(dazName + rig_label("jHead"), dazName + rig_label("Head_ctrl"))

        self.makeChildKeepPos(dazName + rig_label("Head_ctrl"), dazName + rig_label("Neck_ctrl"))
        self.makeChildKeepPos(dazName + rig_label("Neck_ctrl"), dazName + rig_label("ChestUpper_ctrl"))
        self.makeChildKeepPos(dazName + rig_label("Chest_ctrl"), dazName + rig_label("AbdomenUpper_ctrl"))
        self.makeChildKeepPos(dazName + rig_label("Spine_ctrl"), dazName + rig_label("Pelvis_ctrl"))

        self.makeChildKeepPos(dazName + rig_label("AbdomenUpper_ctrl"), dazName + rig_label("Spine_ctrl"))
        self.makeChildKeepPos(dazName + rig_label("ChestUpper_ctrl"), dazName + rig_label("Chest_ctrl"))

        self.makeChildKeepPos(
            dazName + rig_label("jUpLeg.Pole") + sideName, dazName + rig_label("Pelvis_ctrl")
        )
        self.makeChildKeepPos(
            dazName + rig_label("jArm.Pole") + sideName, dazName + rig_label("ChestUpper_ctrl")
        )
        self.makeChildKeepPos(
            dazName + rig_label("IK_Hand") + sideName, dazName + rig_label("ChestUpper_ctrl")
        )

        self.makeChildKeepPos(
            dazName + rig_label("Collar_ctrl") + sideName, dazName + rig_label("ChestUpper_ctrl")
        )
        self.makeChildKeepPos(
            dazName + rig_label("Collar_ctrl___R") + sideName, dazName + rig_label("ChestUpper_ctrl")
        )
        if sideName == "":
            self.makeNull(dazName + "IKM_Controls", dazName + rig_label("jPelvis"), "ROOT")
            self.makeChildKeepPos(dazName + rig_label("Pelvis_ctrl"), dazName + "IKM_Controls")

        self.makeChildKeepPos(dazName + rig_label("Foot_Platform"), dazName + rig_label("Foot_PlatformBase"))
        self.makeChildKeepPos(dazName + rig_label("Foot_PlatformBase"), dazName + "IKM_Controls")

        self.makeChildKeepPos(dazName + rig_label("ForearmTwist_ctrl"), dazName + rig_label("jForeArm"))
        self.makeChildKeepPos(
            dazName + rig_label("ForearmTwist_ctrl___R"), dazName + rig_label("jForeArm___R")
        )

        dazToC4Dutils().initialDisplaySettings()


class alignFingersFull:
    def fixRotations(self, jointName):
        doc = documents.GetActiveDocument()
        try:
            obj = doc.SearchObject(jointName)
            obj[c4d.ID_BASEOBJECT_ROTATION_ORDER] = 5

            objRotX = obj.GetAbsRot()[0]
            objRotY = obj.GetAbsRot()[1]
            objRotZ = obj.GetAbsRot()[2]
            obj.SetAbsRot(c4d.Vector(objRotX, 0, 0))
        except:
            print("FixR skipped...")

    def AlignBoneChain(
        self, rootBone, upAxis, primaryAxis=1, primaryDirection=0, upDirection=4
    ):
        doc = documents.GetActiveDocument()
        try:
            dzc4d.deselect_all()  # Deselect All
            joint = doc.SearchObject(rootBone)

            normalNull = doc.SearchObject("normalNull")  # Normal Null ...!!..

            doc.SetActiveObject(joint, c4d.SELECTION_NEW)
            c4d.CallCommand(1021334, 1021334)
            c4d.CallCommand(1021334)  # Joint Align Tool
            tool = c4d.plugins.FindPlugin(doc.GetAction(), c4d.PLUGINTYPE_TOOL)
            if tool is not None:
                tool[c4d.ID_CA_JOINT_ALIGN_PRIMARY_AXIS] = primaryAxis
                tool[c4d.ID_CA_JOINT_ALIGN_PRIMARY_DIRECTION] = primaryDirection
                tool[c4d.ID_CA_JOINT_ALIGN_UP_AXIS] = upAxis
                tool[c4d.ID_CA_JOINT_ALIGN_UP_DIRECTION] = upDirection
                tool[c4d.ID_CA_JOINT_ALIGN_UP_FROMPREV] = True
                tool[c4d.ID_CA_JOINT_ALIGN_CHILDREN] = True
                tool[c4d.ID_CA_JOINT_ALIGN_UP_LINK] = normalNull
                c4d.CallButton(tool, c4d.ID_CA_JOINT_ALIGN)
        except:
            print("AlignBC Skipped...")
        c4d.EventAdd()

    def alignJoints(self, jointName):
        doc = documents.GetActiveDocument()
        try:
            obj = doc.SearchObject(jointName)

            obj[c4d.ID_CA_JOINT_OBJECT_BONE_AXIS] = 1
            c4d.CallCommand(1019883)  # Align
        except:
            print("alignPass skipped...")
        c4d.EventAdd()

    def constraintClamp(self, obj, normalPolyObj):
        doc = documents.GetActiveDocument()
        constraintTAG = c4d.BaseTag(1019364)
        constraintTAG[c4d.ID_CA_CONSTRAINT_TAG_CLAMP] = True
        constraintTAG[50004, 1] = 4  # To: Surface
        constraintTAG[50004, 3] = 5  # Align: Z-
        constraintTAG[50004, 2] = 3  # Mode: Fix Axis
        constraintTAG[50004, 4] = 4  # As: Normal
        constraintTAG[50001] = normalPolyObj
        obj.InsertTag(constraintTAG)
        c4d.EventAdd()

    def generateNormalFromObjs(self, target1, target2, target3):
        doc = documents.GetActiveDocument()
        obj1 = doc.SearchObject("normalNull")
        obj2 = doc.SearchObject("normalPoly")
        obj3 = doc.SearchObject("normalPos1")
        obj4 = doc.SearchObject("normalPos2")
        obj5 = doc.SearchObject("normalPos3")

        try:
            obj1.Remove()
        except:
            pass
        try:
            obj2.Remove()
        except:
            pass
        try:
            obj3.Remove()
        except:
            pass
        try:
            obj4.Remove()
        except:
            pass
        try:
            obj5.Remove()
        except:
            pass

        objNull = c4d.BaseObject(c4d.Onull)
        objNull.SetName("normalNull")
        doc.InsertObject(objNull)
        c4d.EventAdd()

        obj1 = c4d.BaseObject(c4d.Onull)
        obj1.SetName("normalPos1")
        doc.InsertObject(obj1)
        obj2 = c4d.BaseObject(c4d.Onull)
        doc.InsertObject(obj2)
        obj2.SetName("normalPos2")
        obj3 = c4d.BaseObject(c4d.Onull)
        doc.InsertObject(obj3)
        obj3.SetName("normalPos3")

        targetObj1 = doc.SearchObject(target1)
        targetObj2 = doc.SearchObject(target2)
        targetObj3 = doc.SearchObject(target3)

        obj1.SetMg(targetObj1.GetMg())
        obj2.SetMg(targetObj2.GetMg())
        obj3.SetMg(targetObj3.GetMg())

        mypoly = c4d.BaseObject(c4d.Opolygon)  # Create an empty polygon object
        mypoly.ResizeObject(4, 1)  # New number of points, New number of polygons

        mypoly.SetPoint(0, obj1.GetAbsPos())
        mypoly.SetPoint(1, obj2.GetAbsPos())
        mypoly.SetPoint(2, obj3.GetAbsPos())
        mypoly.SetPoint(3, obj3.GetAbsPos())

        mypoly.SetName("normalPoly")
        mypoly.SetPolygon(
            0, c4d.CPolygon(0, 1, 2, 3)
        )  # The Polygon's index, Polygon's points
        doc.InsertObject(mypoly, None, None)
        mypoly.Message(c4d.MSG_UPDATE)

        doc.SetActiveObject(mypoly, c4d.SELECTION_NEW)
        c4d.CallCommand(14039)  # Optimize...
        c4d.CallCommand(1011982)  # Center Axis to

        objNull.SetMg(mypoly.GetMg())

        c4d.EventAdd()

        self.constraintClamp(objNull, mypoly)
        c4d.EventAdd()

    def start(self, modelName, lastFinger=""):
        doc = c4d.documents.GetActiveDocument()
        # modelName = 'Human_Builder_' #Replace with model name....
        jHand = modelName + rig_label("jHand")
        jIndex1 = modelName + rig_label("jIndex1")
        jIndex2 = modelName + rig_label("jIndex2")
        jIndex3 = modelName + rig_label("jIndex3")
        jMiddle1 = modelName + rig_label("jMiddle1")
        jMiddle2 = modelName + rig_label("jMiddle2")
        jMiddle3 = modelName + rig_label("jMiddle3")
        jRing1 = modelName + rig_label("jRing1")
        jRing2 = modelName + rig_label("jRing2")
        jRing3 = modelName + rig_label("jRing3")
        jPink1 = modelName + rig_label("jPink1")
        jPink2 = modelName + rig_label("jPink2")
        jPink3 = modelName + rig_label("jPink3")
        fingersList = [
            rig_label("jIndex1"),
            rig_label("jIndex2"),
            rig_label("jIndex3"),
            rig_label("jMiddle1"),
            rig_label("jMiddle2"),
            rig_label("jMiddle3"),
            rig_label("jRing1"),
            rig_label("jRing2"),
            rig_label("jRing3"),
            rig_label("jPink1"),
            rig_label("jPink2"),
            rig_label("jPink3"),
        ]

        for j in fingersList:
            self.alignJoints(modelName + j)  # Replace with model name....

        # Generate plane if at least jIndex and other finger present...
        if lastFinger == rig_label("jPink"):
            self.generateNormalFromObjs(jHand, jIndex1, jPink1)
        if lastFinger == rig_label("jRing"):
            self.generateNormalFromObjs(jHand, jIndex1, jRing1)
        if lastFinger == rig_label("jMiddle"):
            self.generateNormalFromObjs(jHand, jIndex1, jMiddle1)

        c4d.DrawViews(
            c4d.DRAWFLAGS_ONLY_ACTIVE_VIEW
            | c4d.DRAWFLAGS_NO_THREAD
            | c4d.DRAWFLAGS_STATICBREAK
        )

        self.AlignBoneChain(modelName + rig_label("jIndex1"), 2, 3, 0, 2)
        self.AlignBoneChain(modelName + rig_label("jMiddle1"), 2, 3, 0, 2)
        self.AlignBoneChain(modelName + rig_label("jRing1"), 2, 3, 0, 2)
        self.AlignBoneChain(modelName + rig_label("jPink1"), 2, 3, 0, 2)

        self.fixRotations(jIndex2)
        self.fixRotations(jIndex3)
        self.fixRotations(jMiddle2)
        self.fixRotations(jMiddle3)
        self.fixRotations(jRing2)
        self.fixRotations(jRing3)
        self.fixRotations(jPink2)
        self.fixRotations(jPink3)

        obj1 = doc.SearchObject("normalNull")
        obj2 = doc.SearchObject("normalPoly")
        obj3 = doc.SearchObject("normalPos1")
        obj4 = doc.SearchObject("normalPos2")
        obj5 = doc.SearchObject("normalPos3")
        try:
            obj1.Remove()
        except:
            pass
        try:
            obj2.Remove()
        except:
            pass
        try:
            obj3.Remove()
        except:
            pass
        try:
            obj4.Remove()
        except:
            pass
        try:
            obj5.Remove()
        except:
            pass

        c4d.EventAdd()
