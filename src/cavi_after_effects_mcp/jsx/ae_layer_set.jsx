$.evalFile(new File(CAVI_LIB));

(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), layer = caviLayer(comp, a.layer), path, applied = [], values = {}, matte, prop, parent;
    // A locked layer refuses every other change, so unlock first and lock last.
    if (a.locked === false) { layer.locked = false; }
    if (a.three_d !== null) { layer.threeDLayer = a.three_d; }
    if (a.motion_blur !== null) {
        if (a.motion_blur && layer instanceof ShapeLayer) { caviGuard3D(comp, layer, "motion blur"); }
        layer.motionBlur = a.motion_blur;
    }
    if (a.name !== null) { layer.name = a.name; }
    if (a.enabled !== null) { layer.enabled = a.enabled; }
    if (a.solo !== null) { layer.solo = a.solo; }
    if (a.shy !== null) { layer.shy = a.shy; }
    if (a.label !== null) { layer.label = a.label; }
    if (a.stretch !== null) { layer.stretch = a.stretch; }
    if (a.start_time !== null) { layer.startTime = a.start_time; }
    if (a.in_point !== null) { layer.inPoint = a.in_point; }
    if (a.out_point !== null) { layer.outPoint = a.out_point; }
    if (a.blend_mode !== null) { layer.blendingMode = caviEnum(BlendingMode, a.blend_mode, "blend mode"); }
    if (a.no_parent) {
        layer.parent = null;
    } else if (a.parent !== null) {
        parent = caviLayer(comp, a.parent);
        layer.parent = parent;
    }
    if (a.track_matte === "none") {
        layer.removeTrackMatte();
    } else if (a.track_matte !== null) {
        matte = a.track_matte;
        layer.setTrackMatte(caviLayer(comp, matte.layer), caviEnum(TrackMatteType, matte.type, "track matte type"));
    }
    for (path in a.properties) {
        if (a.properties.hasOwnProperty(path)) {
            prop = caviProp(layer, path);
            caviSetStatic(prop, a.properties[path]);
            applied.push(path);
            values[path] = prop.value;
        }
    }
    if (a.locked === true) { layer.locked = true; }
    caviReport({comp: comp.name, layer: describeLayer(layer), properties_set: applied, values: values, solo: layer.solo, shy: layer.shy,
        locked: layer.locked, label: layer.label, stretch: layer.stretch, start_time: layer.startTime,
        blend_mode: String(layer.blendingMode), motion_blur: layer.motionBlur, errors: []});
})();
