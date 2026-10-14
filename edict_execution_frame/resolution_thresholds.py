# -*- coding: utf-8 -*-
"""Central thresholds for resolution_status / ambiguity / delegated task gates."""

# task / domain clarification
TASK_CLARIFY_MAX = 0.50
DOMAIN_CLARIFY_MAX = 0.50
TASK_FALLBACK_CLARIFY_MAX = 0.62
AMBIGUITY_TOP1_TOP2_GAP = 0.12
AMBIGUITY_TOP1_LOW = 0.50

# auto_completed vs resolved
AUTO_COMPLETED_TASK_MAX = 0.72

# delegated edict_execution gate（resolver；与 catalog min_task_confidence 可并存）
DELEGATED_MIN_TASK_CONFIDENCE = 0.54
