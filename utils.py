from maya import cmds


def resetSelectedMayaCtrlsTransforms():
    """
    Reset translate, rotate and scale of selected controllers (a controller should be tagged as one using
    Control > Tag As Controller). If nothing selected all controllers are selected.
    :return:
    """
    hint = 'To define controllers please use Control > Tag As Controller'
    attributes = {
        'tx': 0.0, 'ty': 0.0, 'tz': 0.0,
        'rx': 0.0, 'ry': 0.0, 'rz': 0.0,
        'sx': 1.0, 'sy': 1.0, 'sz': 1.0,
    }

    selection = cmds.ls(sl=True)
    ctrls = cmds.controller(q=True, allControllers=True)

    if not ctrls:
        cmds.warning('No controllers found in the scene. {}'.format(hint))
        return
    elif not selection:
        selectedCtrls = ctrls
    else:
        selectedCtrls = set(ctrls).intersection(selection)

        if not selectedCtrls:
            cmds.warning('No controllers selected. {}'.format(hint))
            return

    for ctrl in selectedCtrls:
        for attr, defaultValue in attributes.items():
            plug = '{}.{}'.format(ctrl, attr)

            try:
                cmds.setAttr(plug, defaultValue)
            except RuntimeError:
                pass
