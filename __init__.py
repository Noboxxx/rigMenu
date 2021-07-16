from maya import cmds, mel, OpenMayaUI
from PySide2 import QtWidgets
from shiboken2 import wrapInstance
from functools import partial


class Chunk(object):

    def __init__(self, name=''):
        self.name = str(name)

    def __enter__(self):
        cmds.undoInfo(openChunk=True, chunkName=self.name)

    def __exit__(self, exc_type, exc_val, exc_tb):
        cmds.undoInfo(closeChunk=True)


def chunk(func):
    def wrapper(*args, **kwargs):
        with Chunk(name=func.__name__):
            return func(*args, **kwargs)

    return wrapper


class RigUtils(object):
    @classmethod
    @chunk
    def locator_on_gizmo(cls):
        gizmo_position = cmds.manipMoveContext('Move', q=True, p=True)

        if gizmo_position:
            loct, = cmds.spaceLocator()
            cmds.xform(loct, translation=gizmo_position)
        else:
            cmds.warning('You should be using the Move Tool to be proceed.')

    @classmethod
    def get_skinned_joints(cls, mesh):
        joints = list()
        skin_clusters = [n for n in cmds.listHistory(mesh) or list() if cmds.objectType(n, isAType='skinCluster')]
        for skin_cluster in skin_clusters:
            joints += cmds.skinCluster(skin_cluster, query=True, inf=True) or list()
        joints = list(set(joints))
        joints.sort()
        return joints

    @classmethod
    @chunk
    def select_skinned_joints(cls):
        joints = list()
        for node in cmds.ls(sl=True) or list():
            joints += cls.get_skinned_joints(node)
        if joints:
            joints = list(set(joints))
            joints.sort()
            cmds.select(joints)

    @classmethod
    def get_skin_cluster(cls, mesh):
        for node in cmds.listHistory(mesh) or list():
            if cmds.objectType(node, isAType='skinCluster'):
                return node
        return None

    @classmethod
    @chunk
    def transfer_skin(cls):
        attributes = (
            'skinningMethod', 'useComponents', 'deformUserNormals', 'dqsSupportNonRigid',
            'dqsScaleX', 'dqsScaleY', 'dqsScaleZ', 'normalizeWeights', 'weightDistribution',
            'maintainMaxInfluences', 'maxInfluences', 'envelope'
        )
        selection = cmds.ls(sl=True) or list()
        if len(selection) > 1:
            parent = selection[0]
            children = selection[1:]

            parent_skin_cluster = cls.get_skin_cluster(parent)

            data = list()
            for attr in attributes:
                data.append((attr, cmds.getAttr('{0}.{1}'.format(parent_skin_cluster, attr))))

            joints = cls.get_skinned_joints(parent)
            for child in children:
                # Wipe out any previous skinCluster on dest mesh
                if True in [cmds.objectType(node, isAType='skinCluster') for node in cmds.listHistory(child) or list()]:
                    cmds.skinCluster(child, e=True, unbind=True)

                # Skin dest mesh with joints' meshes
                new_skin_cluster, = cmds.skinCluster(child, joints)

                for attr, value in data:
                    cmds.setAttr('{0}.{1}'.format(new_skin_cluster, attr), value)

                # Transfer the skin
                cmds.copySkinWeights(parent, child, noMirror=True, surfaceAssociation='closestPoint', influenceAssociation=('name', 'closestJoint'))
        else:
            cmds.warning('Two meshes should be at least selected.')

        cmds.select(selection)

    @classmethod
    @chunk
    def scale_joints_up(cls):
        current = cmds.jointDisplayScale(q=True)
        new = current * 1.5
        cmds.jointDisplayScale(new)

    @classmethod
    @chunk
    def scale_joints_down(cls):
        current = cmds.jointDisplayScale(q=True)
        new = current * 0.75
        cmds.jointDisplayScale(new)

    @classmethod
    @chunk
    def toggle_ctrls_visibility(cls):
        for index in range(10):
            panel = 'modelPanel{0}'.format(index)
            try:
                if cmds.modelEditor(panel, q=True, nc=True):
                    cmds.modelEditor(panel, e=True, nc=False)
                else:
                    cmds.modelEditor(panel, e=True, nc=True)
            except:
                continue

    @classmethod
    @chunk
    def toggle_joints_visibility(cls):
        for index in range(10):
            panel = 'modelPanel{0}'.format(index)
            try:
                if cmds.modelEditor(panel, q=True, j=True):
                    cmds.modelEditor(panel, e=True, jx=False, j=False)
                else:
                    cmds.modelEditor(panel, e=True, jx=True, j=True)
            except:
                continue

    # @classmethod
    # @chunk
    # def toggle_joints_visibility(cls):
    #     draw_style_str = 'drawStyle'
    #     joints = cmds.ls('*_jnt', type='joint') or list()
    #
    #     if joints:
    #         reversed_state = 2 if cmds.getAttr("{0}.{1}".format(joints[0], draw_style_str)) == 0 else 0
    #         for joint in joints:
    #             cmds.setAttr('{0}.{1}'.format(joint, draw_style_str), reversed_state)
    #
    #
    #         for index in range(10):
    #             panel = 'modelPanel{0}'.format(index)
    #             try:
    #                 if reversed_state == 2:
    #                     cmds.modelEditor(panel, e=True, jx=False, j=False)
    #                 else:
    #                     cmds.modelEditor(panel, e=True, jx=True, j=True)
    #             except:
    #                 continue

    @classmethod
    @chunk
    def toggle_wireframe(cls):
        for index in range(10):
            panel = 'modelPanel{0}'.format(index)
            try:
                if cmds.modelEditor(panel, q=True, wos=True):
                    cmds.modelEditor(panel, e=True, wos=False)
                else:
                    cmds.modelEditor(panel, e=True, wos=True)
            except:
                continue

    @classmethod
    def print_non_unique_nodes(cls):
        nodes = list()
        not_unique = list()
        for node in cmds.ls(dag=True, shortNames=True) or list():
            node = node.split('|')[-1]
            if not node in nodes:
                nodes.append(node)
            else:
                not_unique.append(node)

        if not_unique:
            for node in not_unique:
                print(node)
            cmds.warning('Your scene contains non-unique node names.')
        else:
            cmds.warning('Your scene is clear.')

    @classmethod
    def print_selection(cls):
        s = '('
        for node in cmds.ls(sl=True):
            s += '\'{0}\', '.format(node)

        print('{0})'.format(s))

    @classmethod
    @chunk
    def reset_transforms(cls):
        from xi.project_utils.utils import mayaUtils

        def reset_ctrls():
            seled_ctrls = mayaUtils.Ctrl.get_selected()
            ctrls = seled_ctrls if seled_ctrls else mayaUtils.Ctrl.get_all()
            for ctrl in ctrls:
                ctrl.reset(transforms=True, options=False)

        reset_ctrls()

    @classmethod
    @chunk
    def select_ctrls(cls):
        from xi.project_utils.utils import mayaUtils

        def select_ctrls():
            cmds.select(mayaUtils.Ctrl.get_all(namespace=None))

        select_ctrls()

    @classmethod
    def node_editor(cls):
        mel.eval('NodeEditorWindow;')

    @classmethod
    def script_editor(cls):
        mel.eval('ScriptEditor;')

    @classmethod
    def ng_skin_tools2(cls):
        import ngSkinTools2
        ngSkinTools2.open_ui()

    @classmethod
    @chunk
    def create_global_local_ctrls(cls, position=(0, 0, 0), rotation=(0, 0, 0), id_='default', index=0, radius=1):
        global_ctrl_name = '{0}_global_C{1}_ctl'.format(id_, index)
        while cmds.objExists(global_ctrl_name):
            index += 1
            global_ctrl_name = '{0}_global_C{1}_ctl'.format(id_, index)

        # Create hierarchy
        global_ctrl, = cmds.circle(name=global_ctrl_name, ch=False, normal=(0, 1, 0), radius=radius * 1.2)

        global_ctrl_srt_name = '{0}_global_C{1}_srt'.format(id_, index)
        global_ctrl_srt = cmds.group(empty=True, name=global_ctrl_srt_name)

        local_ctrl_name = '{0}_local_C{1}_ctl'.format(id_, index)
        local_ctrl, = cmds.circle(name=local_ctrl_name, ch=False, normal=(0, 1, 0), radius=radius)

        local_joint_name = '{0}_local_C{1}_jnt'.format(id_, index)
        cmds.select(clear=True)
        local_joint = cmds.joint(name=local_joint_name)

        cmds.parent(local_joint, local_ctrl)
        cmds.parent(local_ctrl, global_ctrl)
        cmds.parent(global_ctrl, global_ctrl_srt)

        cmds.xform(global_ctrl_srt, translation=position)
        cmds.xform(global_ctrl_srt, rotation=rotation)

        # clean ctrls
        for ctrl, color in ((global_ctrl, 6), (local_ctrl, 18)):
            ctrl_shape = ctrl + 'Shape'
            cmds.setAttr('{0}.{1}'.format(ctrl_shape, 'overrideEnabled'), True)
            cmds.setAttr('{0}.{1}'.format(ctrl_shape, 'overrideColor'), color)
            cmds.setAttr('{0}.{1}'.format(ctrl, 'visibility'), lock=True, keyable=False)

        return global_ctrl, local_ctrl, local_joint

    @classmethod
    @chunk
    def create_global_local_ctrls_from_selection(cls, bottom=False):
        selection = cmds.ls(sl=True)

        if not selection:
            return

        # Fetch selection bounding box
        bounding_box = cmds.exactWorldBoundingBox(selection)
        pa = bounding_box[:3]
        pb = bounding_box[3:]

        # Calculate mid point
        if bottom is False:
            mid_point = (
                (pa[0] + pb[0]) / 2,
                (pa[1] + pb[1]) / 2,
                (pa[2] + pb[2]) / 2
            )
        else:
            mid_point = (
                (pa[0] + pb[0]) / 2,
                min((pa[1], pb[1])),
                (pa[2] + pb[2]) / 2
            )

        # Calculate ctrl radius based on distances
        distance_x = abs(pa[0] - pb[0])
        distance_z = abs(pa[2] - pb[2])
        radius = max((distance_x, distance_z)) * .7

        # Get selection id
        id_ = selection[0].split('_')[0]
        id_ = id_[0].lower() + id_[1:]

        # Create hierarchy
        _, _, local_joint = cls.create_global_local_ctrls(position=mid_point, rotation=(0, 0, 0), id_=id_, index=0, radius=radius)

        #Skin
        meshes = list()
        for item in selection:
            item = item.split('.')[0]
            descendents = cmds.listRelatives(item, allDescendents=True) or list()
            for child in descendents + [item]:
                if cmds.objectType(child, isAType='mesh'):
                    if cmds.getAttr('{0}.{1}'.format(child, 'intermediateObject')) is False:
                        meshes.append(child)
        meshes = list(set(meshes))

        for mesh in meshes:
            skin_cluster = cls.get_skin_cluster(mesh)
            if skin_cluster:
                cmds.skinCluster(skin_cluster, e=True, addInfluence=local_joint)
            else:
                cmds.skinCluster(mesh, local_joint)

        cmds.select(selection)

    @classmethod
    def compare_control_set_to_all_ctrls(cls):
        from xi.project_utils.utils import mayaUtils

        cmds.select('ControlSet')
        control_set_members = set(cmds.ls(sl=True) or list())

        ctrls = {str(ctrl) for ctrl in mayaUtils.Ctrl.get_all()}
        print len(control_set_members), len(ctrls)
        for ctrl in ctrls:
            if ctrl not in control_set_members:
                print(ctrl)

    @classmethod
    def create_mesh_attribute(cls):
        selection = cmds.ls(sl=True) or list()

        if len(selection) < 2:
            cmds.warning('Please select at least 2 nodes.')
            return

        parent = selection.pop(0)
        children = selection

        mesh_attr_name = 'Mesh'
        mesh_plug = '{0}.{1}'.format(parent, mesh_attr_name)
        if not cmds.objExists(mesh_plug):
            cmds.addAttr(parent, longName=mesh_attr_name, attributeType='bool', defaultValue=True, keyable=True)

        for child in children:
            vis_plug = '{0}.{1}'.format(child, 'visibility')
            if cmds.objExists(vis_plug):
                cmds.connectAttr(mesh_plug, vis_plug, force=True)
            else:
                cmds.warning('Visibility attribute does not exist on this node \'{0}\''.format(child))

    @classmethod
    def bs_controls(cls):
        from bsControls import bs_controlsUI
        bs_controlsUI.BSControlsUI().bsControlsUI()

    @classmethod
    def unlock_modeling(cls):
        geo_grp = 'geometry'

        if not cmds.objExists(geo_grp):
            cmds.warning('The group \'{}\' hasnt been found.'.format(geo_grp))
            return

        geo_grp_descendents = cmds.listRelatives(geo_grp, allDescendents=True, type=('transform', 'mesh')) or list()

        for node in geo_grp_descendents + [geo_grp]:
            try:
                cmds.setAttr(node + '.overrideEnabled', False)
                cmds.setAttr(node + '.overrideDisplayType', False)
            except:
                cmds.warning('Unable to unset override to \'{}\'.'.format(node))
            # setAttr "head_C0_geo.overrideEnabled" 1;
            # setAttr "head_C0_geo.overrideDisplayType" 2;
            # setAttr "head_C0_geo.overrideDisplayType" 0;
            # setAttr "head_C0_geo.overrideEnabled" 0;

    @classmethod
    def lock_modeling(cls):
        geo_grp = 'geometry'

        if not cmds.objExists(geo_grp):
            cmds.warning('The group \'{}\' hasnt been found.'.format(geo_grp))
            return

        cmds.setAttr(geo_grp + '.overrideEnabled', True)
        cmds.setAttr(geo_grp + '.overrideDisplayType', 2)

    @classmethod
    def lock_rig(cls):
        cls.lock_all_vis_attrs_on_ctrls()
        cls.lock_modeling()
        cls.remove_all_ng_skin_tools2()
        cls.optimize_skin_clusters()
        cls.delete_unused_nodes()

    @classmethod
    def lock_all_vis_attrs_on_ctrls(cls):
        from xi.project_utils.utils import mayaUtils

        for ctrl in mayaUtils.Ctrl.get_all():
            cmds.setAttr('{0}.{1}'.format(ctrl, 'v'), lock=True, keyable=False)

    @classmethod
    def optimize_skin_clusters(cls):
        for mesh in cmds.ls(type='mesh'):
            if 'skinCluster' in [cmds.objectType(node) for node in cmds.listHistory(mesh) or list()]:
                print mesh
                cmds.select(mesh)
                try:
                    mel.eval('removeUnusedInfluences;')
                except:
                    pass

    @classmethod
    def remove_all_ng_skin_tools2(cls):
        from ngSkinTools2.operations import removeLayerData
        removeLayerData.removeCustomNodes()

    @classmethod
    def delete_unused_nodes(cls):
        mel.eval('MLdeleteUnused;')

    @classmethod
    def open_ctrl_shaper(cls):
        from ctrlShaper import ctrlShaperUi
        ctrlShaperUi.CtrlShaperUi().show()

    @classmethod
    def reset_grp(cls):
        for node in cmds.ls(sl=True) or list():
            node_parent = cmds.listRelatives(node, parent=True)
            rst = cmds.group(name=node + '_rst#', empty=True)
            node_matrix = cmds.xform(node, q=True, matrix=True)
            cmds.xform(rst, matrix=node_matrix)
            cmds.parent(node, rst)
            if node_parent:
                cmds.parent(rst, node_parent[0])


class MainMenu(object):
    label = 'Default'

    def __init__(self, widget):
        self.widget = widget

    @classmethod
    def get_widget(cls, object_name, type_):
        pointer = OpenMayaUI.MQtUtil.findControl(object_name)
        return wrapInstance(long(pointer), type_)

    def fill_up_menu(self):
        default_action = QtWidgets.QAction('default', self.widget)
        self.addAction(default_action)

    @classmethod
    def display(cls):
        if cmds.menu(cls.__name__, q=True, exists=True):
            cls.delete()
        cmds.menu(cls.__name__, parent='MayaWindow', label=cls.label, tearOff=True)
        main_menu = cls(cls.get_widget(cls.__name__, QtWidgets.QMenu))
        main_menu.fill_up_menu()
        return main_menu

    @classmethod
    def get(cls):
        if cmds.menu(cls.__name__, q=True, exists=True):
            return cls(cls.get_widget(cls.__name__, QtWidgets.QMenu))
        return None

    def addMenu(self, menu):
        self.widget.addMenu(menu)

    def addAction(self, action):
        self.widget.addAction(action)

    @classmethod
    def delete(cls):
        cmds.deleteUI(cls.__name__)


class RigMainMenu(MainMenu):
    label = 'Rig'

    def fill_up_menu(self):
        data = (
            ('Locator on Gizmo', RigUtils.locator_on_gizmo, ('Ctrl+L',)),
            ('Reset Group', RigUtils.reset_grp, ('Ctrl+Alt+G',)),

            ('Skin', None, None),
            ('Select Skinned Joints', RigUtils.select_skinned_joints, None),
            ('Transfer Skin', RigUtils.transfer_skin, None),

            ('Display', None, None),
            ('Scale Joints Up', RigUtils.scale_joints_up, ('Ctrl++',)),
            ('Scale Joints Down', RigUtils.scale_joints_down, ('Ctrl+-',)),
            ('Toggle Ctrls Visibility', RigUtils.toggle_ctrls_visibility, ('7',)),
            ('Toggle Joints Visibility', RigUtils.toggle_joints_visibility, ('9',)),
            ('Toggle Wireframe Visibility', RigUtils.toggle_wireframe, ('8',)),

            ('Windows', None, None),
            ('Node Editor', RigUtils.node_editor, ('Shift+N',)),
            ('Script Editor', RigUtils.script_editor, ('Shift+S',)),

            ('Misc', None, None),
            ('Print Selection', RigUtils.print_selection, None),
            ('Print Non-Unique Nodes', RigUtils.print_non_unique_nodes, None),

            ('Plug-ins', None, None),
            ('ngSkinTools2', RigUtils.ng_skin_tools2, ('Shift+G',)),
            ('bsControls', RigUtils.bs_controls, ('Shift+O',)),
            ('ctrlShaper', RigUtils.open_ctrl_shaper, None),

            ('X', None, None),
            ('Reset Transforms', RigUtils.reset_transforms, ('Ctrl+T',)),
            ('Select Ctrls', RigUtils.select_ctrls, ('Ctrl+Shift+C',)),
            ('Check ControlSet', RigUtils.compare_control_set_to_all_ctrls, None),
            ('Create Mesh Attribute', RigUtils.create_mesh_attribute, ('ctrl+M',)),
            ('Unlock Geo', RigUtils.unlock_modeling, None),
            ('Lock Geo', RigUtils.lock_modeling, None),
            ('Global Local', RigUtils.create_global_local_ctrls_from_selection, ('Ctrl+Alt+C',)),
            ('Global Local (bottom)', partial(RigUtils.create_global_local_ctrls_from_selection, bottom=True), ('Ctrl+Alt+V',)),
            ('Lock Rig', RigUtils.lock_rig, None),
        )
        for label, func, shortcuts in data:
            act = QtWidgets.QAction(label, self.widget)
            if func:
                act.triggered.connect(func)
                if shortcuts:
                    act.setShortcuts(shortcuts)
            else:
                act.setSeparator(True)

            self.addAction(act)


def display():
    RigMainMenu.display()
