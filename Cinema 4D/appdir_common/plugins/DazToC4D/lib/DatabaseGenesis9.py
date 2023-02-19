import c4d

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

constraint_joints = [
    ["hip", "j_hip"],
    ["pelvis", "j_pelvis"],
    ["spine1", "j_spine1"],
    ["spine2", "j_spine2"],
    ["spine3", "j_spine3"],
    ["spine4", "j_spine4"],
    ["neck1", "j_neck1"],
    ["head", "j_head"],
    ["shoulder", "j_shoulder"],
    ["upperarm", "j_upperarm"],
    ["forearm", "j_forearm"],
    ["upperarmtwist1", "j_upperarmtwist1"],
    ["forearmtwist1", "j_forearmtwist1"],
    ["hand", "j_hand"],
    ["index1", "j_index1"],
    ["index2", "j_index2"],
    ["index3", "j_index3"],
    ["mid1", "j_mid1"],
    ["mid2", "j_mid2"],
    ["mid3", "j_mid3"],
    ["ring1", "j_ring1"],
    ["ring2", "j_ring2"],
    ["ring3", "j_ring3"],
    ["pinky1", "j_pinky1"],
    ["pinky2", "j_pinky2"],
    ["pinky3", "j_pinky3"],
    ["thumb1", "j_thumb1"],
    ["thumb2", "j_thumb2"],
    ["thumb3", "j_thumb3"],
    ["thightwist1", "j_thightwist1"],
    ["thigh", "j_thigh"],
    ["shin", "j_shin"],
    ["foot", "j_foot"],
    ["toes", "j_toes"],
    ["midtoe2", "j_toes_end"], # not sure if we need it
    ["midtoe1", "j_midtoe1"],
]

rig_joints = [
    ["hip", "j_hip"],
    ["pelvis", "j_pelvis"],
    ["spine1", "j_spine1"],
    ["spine2", "j_spine2"],
    ["spine3", "j_spine3"],
    ["spine4", "j_spine4"],
    ["neck1", "j_neck1"],
    ["head", "j_head"],
    ["shoulder", "j_shoulder"],
    ["upperarm", "j_upperarm"],
    ["forearm", "j_forearm"],
    ["upperarmtwist1", "j_upperarmtwist1"],
    ["forearmtwist1", "j_forearmtwist1"],
    ["hand", "j_hand"],
    ["index1", "j_index1"],
    ["index2", "j_index2"],
    ["index3", "j_index3"],
    ["mid1", "j_mid1"],
    ["mid2", "j_mid2"],
    ["mid3", "j_mid3"],
    ["ring1", "j_ring1"],
    ["ring2", "j_ring2"],
    ["ring3", "j_ring3"],
    ["pinky1", "j_pinky1"],
    ["pinky2", "j_pinky2"],
    ["pinky3", "j_pinky3"],
    ["thumb1", "j_thumb1"],
    ["thumb2", "j_thumb2"],
    ["thumb3", "j_thumb3"],
    ["thightwist1", "j_thightwist1"],
    ["thigh", "j_thigh"],
    ["shin", "j_shin"],
    ["foot", "j_foot"],
    ["toes", "j_toes"],
    ["midtoe2", "j_toes_end"],
    ["midtoe1", "j_midtoe1"],
]

guides_for_rig = [
    ["hip", "hip"],
    ["spine1", "spine1"],
    ["spine2", "spine2"],
    ["spine3", "spine3"],
    ["spine4", "spine4"],
    ["neck1", "neck1"],
    ["head", "head"],
    ["head_end", "head_end"],
    ["shoulder", "l_shoulder"],
    ["upperarm", "l_upperarm"],
    ["forearm", "l_forearm"],
    ["upperarmtwist1", "l_upperarmtwist1"],
    ["forearmtwist1", "l_forearmtwist1"],
    ["hand", "l_hand"],
    ["index1", "l_index1"],
    ["index2", "l_index2"],
    ["index3", "l_index3"],
    ["index_end", "l_index_end"],
    ["mid1", "l_mid1"],
    ["mid2", "l_mid2"],
    ["mid3", "l_mid3"],
    ["mid_end", "l_mid_end"],
    ["ring1", "l_ring1"],
    ["ring2", "l_ring2"],
    ["ring3", "l_ring3"],
    ["ring_end", "l_ring_end"],
    ["pinky1", "l_pinky1"],
    ["pinky2", "l_pinky2"],
    ["pinky3", "l_pinky3"],
    ["pinky_end", "l_pinky_end"],
    ["thumb1", "l_thumb1"],
    ["thumb2", "l_thumb2"],
    ["thumb3", "l_thumb3"],
    ["thumb_end", "l_thumb_end"],
    ["thightwist1", "l_thightwist1"],
    ["thigh", "l_thigh"],
    ["shin", "l_shin"],
    ["foot", "l_foot"],
    ["toes", "l_toes"],
    ["toes_end", "l_midtoe2"],
    ["midtoe1", "l_midtoe1"],
]

guides_to_mirror = [
    "shoulder",
    "upperarm",
    "forearm",
    "upperarmtwist1",
    "forearmtwist1",
    "hand",
    "index1",
    "index2",
    "index3",
    "index_end",
    "mid1",
    "mid2",
    "mid3",
    "mid_end",
    "ring1",
    "ring2",
    "ring3",
    "ring_end",
    "pinky1",
    "pinky2",
    "pinky3",
    "pinky_end",
    "thumb1",
    "thumb2",
    "thumb3",
    "thumb_end",
    "thightwist1",
    "thigh",
    "shin",
    "foot",
    "toes",
    "toes_end",
    "midtoe1",
]

""" [ ctrl_joint, Parent, Guide ]
"""
center_joints = [
    ["j_pelvis", "", "pelvis"],
    ["j_spine1", "j_pelvis", "spine1"],
    ["j_spine2", "j_spine1", "spine2"],
    ["j_spine3", "j_spine2", "spine3"],
    ["j_spine4", "j_spine3", "spine4"],
    ["j_neck1", "j_spine4", "neck1"],
    ["j_head", "j_neck1", "head"],
    ["j_head_end", "j_head", "head_end"],
]

arm_joints = [
    ["j_shoulder", "j_spine4", "shoulder"],
    ["j_upperarm", "j_shoulder", "upperarm"],
    ["j_forearm", "j_upperarm", "forearmtwist1"],
    ["j_hand", "j_forearm", "hand"],
]

leg_joints = [
    ["j_thigh", "j_pelvis", "thigh"],
    ["j_shin", "j_thigh", "shin"],
    ["j_foot", "j_shin", "foot"],
    ["j_foot2", "", "foot"],
    ["j_toes", "j_foot2", "toes"],
    ["j_toes_end", "j_toes", "toes_end"],
]

thumb_joints = [
    ["j_thumb1", "", "thumb1"],
    ["j_thumb2", "j_thumb1", "thumb2"],
    ["j_thumb3", "j_thumb2", "thumb3"],
    ["j_thumb_end", "j_thumb3", "thumb_end"],
]

""" [ ctrl_shape, joint, preset, constraint, parent ]
"""
ik_controls = [
    ["IK_foot", "j_foot", "zeroRotInvisible"],
    ["toe_Rot", "j_toes", "sphereToe"],
    ["foot_Roll", "j_toes", "cube"],
    ["IK_hand", "j_hand", "cube"],
    ["shoulder_ctrl", "j_shoulder", "collar"],
    ["foot_Platform", "IK_foot", "foot_Platform"],
    ["toes_end_ctrl", "j_toes_end", "none"],
    ["pelvis_ctrl", "j_pelvis", "pelvis"],
    ["forearmtwist_ctrl", "l_forearmtwist2", "twist"],
    ["forearmtwist_ctrl___R", "r_forearmtwist2", "twist"],
    ["spine1_ctrl", "j_spine1", "spine"],
    ["spine2_ctrl", "j_spine2", "spine"],
    ["spine4_ctrl", "j_spine4", "spine"],
    ["foot_PlatformBase", "j_foot", "foot_PlatformNEW"],
    ["foot_PlatformBase___R", "j_foot___R", "foot_PlatformNEW"],
    ["spine3_ctrl", "j_spine3", "spine"],
    ["neck1_ctrl", "j_neck1", "neck"],
    ["head_ctrl", "j_head", "head"],
]

ik_tags = [
    ["j_thightwist1", "j_foot", "IK_foot", "j_thightwist1.Pole", "thigh", "Negative"],
    ["j_upperarmtwist1", "j_hand", "IK_hand", "j_upperarmtwist1.Pole", "upperarm", ""],
]

daz_controls = [
    ["IK_foot", "foot", "zeroRotInvisible", "None"],
    ["toe_Rot", "toe", "sphereToe", "None"],
    ["foot_Roll", "toe", "cube", "None"],
    ["IK_hand", "hand", "cube", "None"],
    ["shoulder_ctrl", "shoulder", "collar", ""],
    ["foot_Platform", "IK_foot", "foot_Platform", "UPVECTOR"],
    ["pelvis_ctrl", "hip", "pelvis"],
    ["forearmtwist2_ctrl", "l_forearmtwist2", "twist"],
    ["forearmtwist2_ctrl___R", "r_forearmtwist2", "twist"],
    ["spine1_ctrl", "spine1", "spine"],
    ["spine2_ctrl", "spine2", "spine"],
    ["spine4_ctrl", "spine4", "spine"],
    ["foot_PlatformBase", "foot", "foot_PlatformNEW"],
    ["spine3_ctrl", "spine3", "spine"],
    ["neck1_ctrl", "neck1", "neck"],
    ["head_ctrl", "head", "head"],
]

daz_tags = [
    ["shin", "foot", "IK_foot", "shin.Pole", "thightwist1", "Negative"],
    #["shin", "foot", "IK_foot", "shin.Pole", "thigh", "Negative"],
    ["upperarmtwist1", "hand", "IK_hand", "j_upperarmtwist1.Pole", "forearmtwist2", ""],
]
