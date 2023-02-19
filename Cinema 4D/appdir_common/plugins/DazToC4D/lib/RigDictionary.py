from c4d import documents
from . import Database
from . import DatabaseGenesis9

def is_g9():
    doc = documents.GetActiveDocument()
    obj = doc.SearchObject("l_forearmtwist2") # this bone seems to be specific to g9
    if obj:
        return True
    return False

# this function transforms a hardcoded label into a translated rig label depending on the model
# I think I wrapped all hardcoded labels in the AutoRig process but I can't be 100% sure.
# Those labels aren't only bones or joints, sometimes they are radixes 
# such as 'Ring' which matches with 'jRing1' and 'jRing2___R' but also 'lRing1' or 'rRing2' depending 
# on the context
#
# since this is hardcoded and can target either a joint, a rig, a constraint or all of them at the same time
# I decided to put the dictionary here instead of the database
# as the database should probably be left as clean as possible
def rig_label(label):
    g9 = is_g9()
    labels = gen9_labels if g9 else gen8_labels
    res = labels.get(label)
    if res:
        return res
    else:
        if g9:
            print("Not found key for "+label)
        return label

def database():
    return gen9_db if is_g9() else gen8_db

# all genesis8 and above labels are left untouched. We are merely remapping the hardcoded labels to themselves
gen8_db = Database
gen8_labels = {
    "hip":"hip"
}

# The main difficulty is the change of convention for Genesis 9 bones compared to Genesis 8.
# We go from a CamelCase with a lowercase prefix (ex: rForeArm)
# to a lowercase with a snake case prefix (ex: r_forearm)
#
# this causes all sorts of problems with the existing code since joints are created and mapped directly onto the bone radix
#
# convention for genesis 9 labels:
#   - all references to g9 bones are no-space all lowercase (ex: upperarm)
#      - exceptions are "end" bones that don't exist normally (ex: head_end)
#   - all references to g9 directional bones are prefixed with 'l_' or 'r_' (ex: l_upperarm)
#   - all joints are the corresponding g9 radix prefixed with 'j_' (ex: j_pelvis)
#   - directional joints are suffixed with '___R' if they're on the right side, nothing on the left side (ex: j_hand and j_hand___R)
#   - all constraints/IK have the associated all lowercase bone name in it (ex: spine4_ctrl)
#      - they can have capitals elsewhere (ex: foot_PlatformBase___R)
#
# most of the rigging is done with data from DatabaseGenesis9
# the rest is hardcoded inside the code, and a mapping converts it with RigDictionary
gen9_db = DatabaseGenesis9
gen9_labels = {
            # CORE
            "hip":"hip",

            # PELVIS TO HEAD
            "jPelvis":"j_pelvis",
            "jChestUpper":"j_spine4",
            "Neck_Start":"neck1",
            "jHead":"j_head",
            "Pelvis_ctrl":"pelvis_ctrl",
            "jSpine":"j_spine1",
            "Spine_ctrl":"spine1_ctrl",
            "AbdomenUpper_ctrl":"spine2_ctrl",
            "jAbdomenUpper":"j_spine2",
            "ChestUpper_ctrl":"spine4_ctrl",
            "Chest_ctrl":"spine3_ctrl",
            "jChest":"j_spine3",
            "Neck_ctrl":"neck1_ctrl",
            "jNeck":"j_neck1",
            "Head_ctrl":"head_ctrl",
            "head":"head",
            "head_end":"head_end",

            # LEG TO FOOT
            "jUpLeg": "j_thigh",
            "jUpLeg___R": "j_thigh___R",
            "jUpLeg.Pole": "j_thightwist1.Pole",
            "jUpLeg.Pole___R":"j_thightwist1.Pole___R",
            "Knee":"shin",
            "LegUpper":"thightwist1",
            "jLeg":"j_shin",
            "jFoot":"j_foot",
            "jFoot___R":"j_foot___R",
            "jFoot2":"j_foot2",
            "Foot":"foot",
            "Foot_Platform":"foot_Platform",
            "Foot_Platform___R": "foot_Platform___R",
            "Foot_PlatformBase":"foot_PlatformBase",
            "Foot_PlatformBase___R":"foot_PlatformBase___R",
            "Foot_PlatformNEW":"foot_PlatformNEW",
            "ForearmTwist_ctrl":"forearmtwist_ctrl",
            "ForearmTwist_ctrl___R":"forearmtwist_ctrl___R",
            "IK_Foot":"IK_foot",
            "Toe_Rot":"toe_rot",
            "Toe_Rot___R":"toe_rot___R",
            "Foot_Roll":"foot_roll",
            "Foot_Roll___R":"foot_roll___R",
            "lFoot":"l_foot",
            "rFoot":"r_foot",
            
            # TOES
            "Toes_end":"toes_end",
            "Toes":"toes",
            "Toe":"toes",
            "jToes_end":"j_toes_end",
            "jToes":"j_toes",
            "ToesEnd":"toes_end_ctrl",
            "lToe":"l_toes",
            "SmallToe4":"pinkytoe1",
            "SmallToe3":"ringtoe1",
            "SmallToe2":"midtoe1",
            "SmallToe1":"indextoe1",
            "BigToe":"bigtoe1",
            
            # COLLAR/SHOULDER
            "Collar":"shoulder",
            "jCollar":"j_shoulder",
            "lCollar":"l_shoulder",
            "Collar_ctrl":"shoulder_ctrl",
            "Collar_ctrl___R":"shoulder_ctrl___R",
            "collar":"shoulder",

            # ARM
            "jArm.Pole":"j_upperarmtwist1.Pole",
            "jArm.Pole___R":"j_upperarmtwist1.Pole___R",
            "Shoulder":"upperarm",
            "jArm":"j_upperarm",
            "lForearmTwist":"l_forearmtwist2",
            "rForearmTwist":"r_forearmtwist2",
            "jForeArm":"j_forearm",
            "jForeArm___R":"j_forearm___R",
            "Elbow":"forearmtwist1",
            "lShldrBend":"l_upperarmtwist1",
            "lForearmBend":"l_forearmtwist1",
            
            # HAND
            "Hand":"hand",
            "jHand":"j_hand",
            "jHand___R":"j_hand___R",
            "IK_Hand":"IK_hand",
            "lHand":"l_hand",
            "rHand":"r_hand",
            
            # FINGERS
            "Index":"index",
            "Middle":"mid",
            "Pinky":"pinky",
            "Ring":"ring",
            "Thumb":"thumb",
            "jIndex":"j_index",
            "jMiddle":"j_mid",
            "jPink":"j_pinky",
            "jPinky":"j_pinky",
            "jRing":"j_ring",
            "jThumb":"j_thumb",
            "Pinky_end":"pinky_end",
            "Pinky3":"pinky3",
            "Pinky2":"pinky2",
            "Pinky1":"pinky1",
            "Ring_end":"ring_end",
            "Ring3":"ring3",
            "Ring2":"ring2",
            "Ring1":"ring1",
            "Middle_end":"mid_end",
            "Middle3":"mid3",
            "Middle2":"mid2",
            "Middle1":"mid1",
            "Index_end":"index_end",
            "Index3":"index3",
            "Index2":"index2",
            "Index1":"index1",
            "Thumb_end":"thumb_end",
            "Thumb2":"thumb2",
            "Thumb3":"thumb3",
            "Thumb1":"thumb1",
            "jPinky_end":"j_pinky_end",
            "jPinky4":"j_pinky4",
            "jPinky3":"j_pinky3",
            "jPinky2":"j_pinky2",
            "jPinky1":"j_pinky1",
            "jPink_end":"j_pinky_end",
            "jPink4":"j_pinky4",
            "jPink3":"j_pinky3",
            "jPink2":"j_pinky2",
            "jPink1":"j_pinky1",
            "jRing_end":"j_ring_end",
            "jRing4":"j_ring4",
            "jRing3":"j_ring3",
            "jRing2":"j_ring2",
            "jRing1":"j_ring1",
            "jMiddle_end":"j_mid_end",
            "jMiddle4":"j_mid4",
            "jMiddle3":"j_mid3",
            "jMiddle2":"j_mid2",
            "jMiddle1":"j_mid1",
            "jIndex_end":"j_index_end",
            "jIndex4":"j_index4",
            "jIndex3":"j_index3",
            "jIndex2":"j_index2",
            "jIndex1":"j_index1",
            "jThumb_end":"j_thumb_end",
            "jThumb2":"j_thumb2",
            "jThumb3":"j_thumb3",
            "jThumb1":"j_thumb1",
            
}