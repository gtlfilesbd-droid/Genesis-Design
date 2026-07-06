"""User-facing workflow role/stage labels (display only; internal keys unchanged)."""

SITE_DESIGN_LEAD_LABEL = 'Site Design Lead'
SITE_DESIGN_LEAD_BY_LABEL = 'Site Design Lead By'
SITE_DESIGN_SUBMIT_DUE_DATE_LABEL = 'Site Design Submit Due Date'
SITE_DESIGN_LEAD_LABEL_SHORT = 'Design Lead'
SITE_DESIGN_LEAD_ACK_LABEL = 'Site Design Lead Acknowledgement'
SITE_DESIGN_LEAD_ACK_SHORT = 'Design Lead Ack'

DESIGN_IN_PROGRESS_LABEL = 'Design In Progress'
DESIGN_IN_PROGRESS_BAR = 'In Progress'


def _ordinal(version):
    if version == 1:
        return '1st'
    if version == 2:
        return '2nd'
    if version == 3:
        return '3rd'
    return f'{version}th'


def designer_submission_label(version, *, in_progress=False, awaiting=False):
    if in_progress:
        return DESIGN_IN_PROGRESS_LABEL
    if awaiting:
        return f'Awaiting {_ordinal(version)} Submission'
    return f'{_ordinal(version)} Submission'


def designer_submission_bar_label(version, *, in_progress=False, awaiting=False):
    if in_progress:
        return DESIGN_IN_PROGRESS_BAR
    if awaiting:
        return f'Awaiting {_ordinal(version)}'
    return f'{_ordinal(version)} Submit'


def bar_label_for_submission_style_label(label):
    if label == DESIGN_IN_PROGRESS_LABEL:
        return DESIGN_IN_PROGRESS_BAR
    if label.startswith('Awaiting ') and label.endswith(' Submission'):
        version_text = label[len('Awaiting '):-len(' Submission')]
        for version in range(1, 20):
            if _ordinal(version) == version_text:
                return designer_submission_bar_label(version, awaiting=True)
        return label
    if label.endswith(' Submission'):
        version_text = label[:-len(' Submission')]
        for version in range(1, 20):
            if _ordinal(version) == version_text:
                return designer_submission_bar_label(version)
        return label
    if label.startswith('HOD Review ('):
        return 'HOD Review'
    return None


def hod_review_label(review_round):
    return f'HOD Review ({_ordinal(review_round)})'
