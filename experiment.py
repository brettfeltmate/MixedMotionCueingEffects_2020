# -*- coding: utf-8 -*-

__author__ = "Brett Feltmate"

import klibs
from klibs import P
from klibs.KLExceptions import TrialException
from klibs.KLConstants import EL_SACCADE_END, EL_FALSE, NA, RC_KEYPRESS, CIRCLE_BOUNDARY, TIMEOUT
from klibs.KLUtilities import deg_to_px, flush, iterable, smart_sleep, boolean_to_logical, pump
from klibs.KLUtilities import line_segment_len as lsl
from klibs.KLKeyMap import KeyMap
from klibs.KLUserInterface import key_pressed
from klibs.KLGraphics import fill, flip, blit, clear
from klibs.KLGraphics.KLDraw import Rectangle, Circle, SquareAsterisk, FixationCross
from klibs.KLCommunication import any_key, message
from klibs.KLBoundary import BoundaryInspector
from klibs.KLBoundary import CircleBoundary

from math import pi, cos, sin
from sdl2 import SDLK_SPACE

BLACK = (0, 0, 0, 255)
WHITE = (255, 255, 255, 255)
RED = (255, 0, 0, 255)

TOP = "top"
BOTTOM = "bottom"
LEFT = "left"
RIGHT = "right"
V_START_AXIS = "vertical"
H_START_AXIS = "horizontal"
ROT_CW = "clockwise"
ROT_CCW = "counterclockwise"
BOX_1 = "top_or_left"
BOX_2 = "bottom_or_right"
SACC_INSIDE = "inside"
SACC_OUTSIDE = "outside"


class MixedMotionCueingEffects_2020(klibs.Experiment):
    # trial data
    saccades = []
    target_acquired = False

    def setup(self):
        pass
        # Generate messages to be displayed during experiment
        self.err_msgs = {}
        if P.saccade_response_cond:
            self.err_msgs['eye'] = "Moved eyes too soon!"
            self.err_msgs['key'] = "Please respond with eye movements only."
            self.err_msgs['early'] = self.err_msgs['key']  # for convenience in logic
        else:
            self.err_msgs['eye'] = "Moved eyes!"
            self.err_msgs['key'] = "Please respond with the spacebar only."
            self.err_msgs['early'] = "Responded too soon!"

        # Stimulus sizes
        self.target_width = deg_to_px(0.5, even=True)  # diameter of target circle (0.5 degrees)
        self.cue_size = deg_to_px(0.5, even=True)  # size of asterisk/fixations (0.5 degrees)
        self.box_size = deg_to_px(0.8, even=True)  # size of placeholder boxes (0.8 degrees)

        # Stimulus Drawbjects
        self.box = Rectangle(self.box_size, stroke=(2, WHITE)).render()
        self.cross_r = FixationCross(self.cue_size, 2, fill=RED).render()
        self.cross_w = FixationCross(self.cue_size, 2, fill=WHITE).render()
        self.circle = Circle(self.target_width, fill=WHITE).render()
        self.asterisk = SquareAsterisk(self.cue_size, 2, fill=WHITE).render()

        # Layout of stimuli

        # offset between centre of boxes and centre of screen, in degrees
        offset_size_deg = P.dm_offset_size if P.development_mode else 7.0
        self.offset_size = deg_to_px(offset_size_deg)
        self.target_locs = {
            TOP: (P.screen_c[0], P.screen_c[1] - self.offset_size),
            RIGHT: (P.screen_c[0] + self.offset_size, P.screen_c[1]),
            BOTTOM: (P.screen_c[0], P.screen_c[1] + self.offset_size),
            LEFT: (P.screen_c[0] - self.offset_size, P.screen_c[1])
        }

        # prepare all animation locations for both rotation directions and starting axes
        self.animation_frames = 15
        animation_duration = 300  # ms
        self.frame_duration = animation_duration / self.animation_frames
        rotation_increment = (pi / 2) / self.animation_frames
        cx, cy = P.screen_c
        self.frames = {
            V_START_AXIS: {ROT_CW: [], ROT_CCW: []},
            H_START_AXIS: {ROT_CW: [], ROT_CCW: []}
        }
        for i in range(0, self.animation_frames):
            l_x_cw = -self.offset_size * cos(i * rotation_increment)
            l_y_cw = self.offset_size * sin(i * rotation_increment)
            l_x_ccw = self.offset_size * cos(i * rotation_increment)
            l_y_ccw = -self.offset_size * sin(i * rotation_increment)
            cw_locs = [(cx + l_x_cw, cy + l_y_cw), (cx - l_x_cw, cy - l_y_cw)]
            ccw_locs = [(cx + l_x_ccw, cy - l_y_ccw), (cx - l_x_ccw, cy + l_y_ccw)]
            self.frames[H_START_AXIS][ROT_CW].append(ccw_locs)
            self.frames[H_START_AXIS][ROT_CCW].append(cw_locs)
            self.frames[V_START_AXIS][ROT_CW].insert(0, cw_locs)
            self.frames[V_START_AXIS][ROT_CCW].insert(0, ccw_locs)

        # Define keymap for ResponseCollector
        self.keymap = KeyMap(
            "speeded response",  # Name
            ["spacebar"],  # UI Label
            ["spacebar"],  # Data Label
            [SDLK_SPACE]  # SDL2 Keycode
        )

        self.bi = BoundaryInspector()
        self.fixation_boundary = deg_to_px(3.0)  # Radius of 3.0º of visual angle
        #self.boundary = CircleBoundary(label = "drift_correct", center=P.screen_c, radius=self.fixation_boundary)
        self.bi.add_boundary(label="drift_correct", bounds=[P.screen_c, self.fixation_boundary], shape="Circle")

    def block(self):

        block_num = P.block_number
        block_count = P.blocks_per_experiment

        # Display progress messages at start of blocks
        if block_num > 1:
            flush()
            fill()
            block_msg = "Completed block {0} of {1}. Press any key to continue."
            block_msg = block_msg.format(block_num - 1, block_count)
            message(block_msg, registration=5, location=P.screen_c)
            flip()
            any_key()

    def setup_response_collector(self):

        # Configure ResponseCollector to read spacebar presses as responses and display
        # the target during the collection period
        box_locs_during_rc = self.box_axis_during_target()
        self.rc.uses(RC_KEYPRESS)
        self.rc.end_collection_event = "task end"
        self.rc.display_callback = self.display_refresh
        self.rc.display_args = [box_locs_during_rc, self.circle, None, self.target_location]
        self.rc.flip = False
        self.rc.keypress_listener.key_map = self.keymap
        self.rc.keypress_listener.interrupts = True

    def trial_prep(self):

        # Infer the cue location based on starting axis (ie. left and top boxes are 'box 1',
        # bottom and right are 'box 2')
        if self.cue_location == BOX_1:
            self.cue_location = LEFT if self.start_axis is H_START_AXIS else TOP
        else:
            self.cue_location = RIGHT if self.start_axis is H_START_AXIS else BOTTOM

        # Reset trial flags
        self.before_target = True
        self.target_acquired = False
        self.moved_eyes_during_rc = False

        # Add timecourse of events to EventManager
        self.evm.register_tickets([
            ("cross fix end", 300),
            ("circle fix end", 1100),  # 800ms after cross fix end
            ("cue end", 1400),  # 300ms after circle fix end
            ("circle box end", 1600),  # 200ms after cue end
            ("animation end", 1900),  # 300ms after circle box end
            ("asterisk end", 2060),  # 160ms after animation end
            ("task end", 4560)  # 2500ms after asterisk end
        ])

        # Perform drift correct with red fixation cross, changing to white upon
        # completion
        self.display_refresh(self.start_axis, self.cross_r)
        self.el.drift_correct(fill_color=BLACK, draw_target=EL_FALSE)
        self.display_refresh(self.start_axis, self.cross_w)
        flush()

    def trial(self):

        while self.evm.before("cross fix end"):
            self.wait_time()
            self.display_refresh(self.start_axis, self.cross_w)

        while self.evm.before("circle fix end"):
            self.wait_time()
            self.display_refresh(self.start_axis, self.circle)

        while self.evm.before("cue end"):
            self.wait_time()
            self.display_refresh(self.start_axis, self.circle, cue=self.cue_location)

        while self.evm.before("circle box end"):
            self.wait_time()
            self.display_refresh(self.start_axis, self.circle)

        current_frame = 0
        while self.evm.before("animation end"):
            self.wait_time()
            if self.animation_trial:
                if current_frame < self.animation_frames:
                    if self.evm.trial_time_ms > (current_frame * self.frame_duration + 1600):
                        box_locs = self.frames[self.start_axis][self.rotation_dir][current_frame]
                        self.display_refresh(box_locs, self.asterisk)
                        current_frame += 1
            else:
                self.display_refresh(self.start_axis, self.asterisk)

        while self.evm.before("asterisk end"):
            self.display_refresh(self.box_axis_during_target(), self.circle)
            self.wait_time()

        flush()
        self.display_refresh(self.box_axis_during_target(), self.circle, target=self.target_location)

        if P.saccade_response_cond:
            self.saccade_data()
            keypress_rt = NA

        if P.keypress_response_cond:
            self.rc.collect()
            keypress_rt = self.rc.keypress_listener.response(rt=True, value=False)

        clear()
        smart_sleep(1000)

        if P.keypress_response_cond:
            if self.target_location == "none" and keypress_rt != TIMEOUT:
                fill()
                message(self.err_msgs['early'], registration=5, location=P.screen_c)
                flip()
                any_key()
            elif self.moved_eyes_during_rc:
                fill()
                message("Moved eyes during response interval!", registration=5, location=P.screen_c)
                flip()
                any_key()

        return {
            "block_num": P.block_number,
            "trial_num": P.trial_number,
            "session_type": 'saccade' if P.saccade_response_cond else 'keypress',
            "cue_location": self.cue_location,
            "target_location": self.target_location,
            "start_axis": self.start_axis,
            "box_rotation": self.rotation_dir if self.animation_trial else NA,
            "animation_trial": str(self.animation_trial).upper(),
            "target_acquired": str(self.target_acquired).upper() if P.saccade_response_cond else NA,
            "keypress_rt": keypress_rt,
            "moved_eyes": str(self.moved_eyes_during_rc).upper() if P.keypress_response_cond else NA
        }

    def trial_clean_up(self):
        if P.trial_id and P.saccade_response_cond:  # won't exist if trial recycled
            # print self.saccades
            # print "\n\n"
            for s in self.saccades:
                s['trial_id'] = P.trial_number
                s['participant_id'] = P.participant_id
                label = 't_{0}_saccade_{1}'.format(P.trial_number, self.saccades.index(s))
                self.db.init_entry('saccades', label)
                for f in s:
                    if f == "end_time":
                        continue
                    self.db.log(f, s[f])
                self.db.insert()
        self.saccades = []
        self.target_acquired = False

    def clean_up(self):
        pass

    def display_refresh(self, boxes=None, fixation=None, cue=None, target=None):
        # In keypress condition, after target presented, check that gaze
        # is still within fixation bounds and print message at end if not
        if P.keypress_response_cond and self.before_target == False:
            if lsl(self.el.gaze(), P.screen_c) > self.fixation_boundary:
                self.moved_eyes_during_rc = True

        fill()
        if boxes is not None:
            if iterable(boxes):
                box_l = boxes
            if boxes == V_START_AXIS:
                box_l = [self.target_locs[TOP], self.target_locs[BOTTOM]]
            if boxes == H_START_AXIS:
                box_l = [self.target_locs[LEFT], self.target_locs[RIGHT]]

            for l in box_l:
                blit(self.box, 5, l)

        if fixation is not None:
            blit(fixation, 5, P.screen_c)

        if cue:
            blit(self.asterisk, 5, self.target_locs[cue])

        if target:
            if target != "none":  # if not catch trial, show target
                blit(self.circle, 5, self.target_locs[target])
            if self.before_target:
                self.before_target = False

        flip()

    def log_and_recycle_trial(self, err_type):
        """
        Renders an error message to the screen and wait for a response. When a
        response is made, the incomplete trial data is logged to the trial_err
        table and the trial is recycled.

        """
        flush()
        fill()
        message(self.err_msgs[err_type], registration=5, location=P.screen_c)
        flip()
        any_key()
        err_data = {
            "participant_id": P.participant_id,
            "block_num": P.block_number,
            "trial_num": P.trial_number,
            "session_type": 'saccade' if P.saccade_response_cond else 'keypress',
            "cue_location": self.cue_location,
            "target_location": self.target_location,
            "start_axis": self.start_axis,
            "box_rotation": self.rotation_dir if self.animation_trial else NA,
            "animation_trial": boolean_to_logical(self.animation_trial),
            "err_type": err_type
        }
        self.database.insert(data=err_data, table="trials_err")
        raise TrialException(self.err_msgs[err_type])

    def wait_time(self):
        # Appropriated verbatim from original code written by John Christie
        if self.before_target:
            if lsl(self.el.gaze(), P.screen_c) > self.fixation_boundary:
                self.log_and_recycle_trial('eye')
            q = pump(True)
            if key_pressed(queue=q):
                if key_pressed(SDLK_SPACE, queue=q):
                    self.log_and_recycle_trial('early')
                else:
                    self.log_and_recycle_trial('key')

    def saccade_data(self):
        # Following code a rehashing of code borrowed from John Christie's original code

        # Get & write time of target onset
        target_onset = self.el.now()
        self.el.write("TARGET_ON %d" % target_onset)

        # Until 2500ms post target onset, or until target fixated
        while self.el.now() - 2500 and not self.target_acquired:
            self.display_refresh(self.box_axis_during_target(), self.circle, target=self.target_location)
            pump()
            # Get end point of saccades made
            queue = self.el.get_event_queue([EL_SACCADE_END])
            # Check to see if saccade was made to target
            for saccade in queue:
                # Get end point of saccade
                gaze = saccade.getEndGaze()
                # Check if gaze fell outside fixation boundary
                if lsl(gaze, P.screen_c) > self.fixation_boundary:
                    # Get distance between gaze and target
                    dist_from_target = lsl(gaze, self.target_locs[self.target_location])
                    # Log if saccade is inside or outside boundary around target
                    accuracy = SACC_OUTSIDE if dist_from_target > self.fixation_boundary else SACC_INSIDE

                    # If more than one saccade
                    if len(self.saccades):
                        # Grab duration of saccade, relative to the previous saccade
                        # Not entirely sure why 4 is added....
                        duration = saccade.getStartTime() + 4 - self.saccades[-1]['end_time']
                    # Otherwise, get duration of saccade relative to target onset
                    else:
                        duration = saccade.getStartTime() + 4 - target_onset

                    # Write saccade info to database
                    if len(self.saccades) < 3:
                        self.saccades.append({
                            "rt": saccade.getStartTime() - target_onset,
                            "accuracy": accuracy,
                            "dist_from_target": dist_from_target,
                            "start_x": saccade.getStartGaze()[0],
                            "start_y": saccade.getStartGaze()[1],
                            "end_x": saccade.getEndGaze()[0],
                            "end_y": saccade.getEndGaze()[1],
                            "end_time": saccade.getEndTime(),
                            "duration": duration
                        })

                    # Target found = True if gaze within boundary surrounding target
                    if dist_from_target <= self.fixation_boundary:
                        self.target_acquired = True
                        break

    def box_axis_during_target(self):
        if self.animation_trial:
            if self.start_axis == V_START_AXIS:
                return H_START_AXIS
            if self.start_axis == H_START_AXIS:
                return V_START_AXIS
        else:
            return self.start_axis
