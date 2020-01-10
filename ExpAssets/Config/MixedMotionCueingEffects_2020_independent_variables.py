from klibs.KLIndependentVariable import IndependentVariableSet

from klibs import P

MixedMotionCueingEffects_2020_ind_vars = IndependentVariableSet()

MixedMotionCueingEffects_2020_ind_vars.add_variable("target_location", str)
MixedMotionCueingEffects_2020_ind_vars.add_variable("cue_location", str)
MixedMotionCueingEffects_2020_ind_vars.add_variable("start_axis", str)
MixedMotionCueingEffects_2020_ind_vars.add_variable("rotation_dir", str)
MixedMotionCueingEffects_2020_ind_vars.add_variable("animation_trial", bool)

MixedMotionCueingEffects_2020_ind_vars["target_location"].add_values("top", "bottom", "left", "right")
MixedMotionCueingEffects_2020_ind_vars["cue_location"].add_values("top_or_left", "bottom_or_right")
MixedMotionCueingEffects_2020_ind_vars["start_axis"].add_values("horizontal", "vertical")
MixedMotionCueingEffects_2020_ind_vars["rotation_dir"].add_values("clockwise", "counterclockwise")
MixedMotionCueingEffects_2020_ind_vars["animation_trial"].add_values(True, False)

if P.keypress_response_cond:
	# If keypress response session, have catch trials with no targets
	MixedMotionCueingEffects_2020_ind_vars["target_location"].add_value("none")

