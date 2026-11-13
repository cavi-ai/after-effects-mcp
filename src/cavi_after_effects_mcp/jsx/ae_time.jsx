$.evalFile(new File(CAVI_LIB));

var BLEND = {NONE: FrameBlendingType.NO_FRAME_BLEND, MIX: FrameBlendingType.FRAME_MIX, PIXEL_MOTION: FrameBlendingType.PIXEL_MOTION};

function remapProperty(layer) {
    var prop;
    layer.timeRemapEnabled = true;
    prop = layer.property("ADBE Time Remapping");
    return prop;
}

function listed(list, time) {
    var k;
    for (k = 0; k < list.length; k++) {
        if (Math.abs(list[k].time - time) < 0.0001) { return true; }
    }
    return false;
}

(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), layer = caviLayer(comp, a.layer), prop, i, before, keys = [], wanted = [];
    if (a.reverse !== null && (a.reverse !== (layer.stretch < 0))) {
        // A reversed layer shows between its out and in points, so keep the earlier edge where it was.
        before = Math.min(layer.inPoint, layer.outPoint);
        layer.stretch = -layer.stretch;
        layer.startTime = layer.startTime + (before - Math.min(layer.inPoint, layer.outPoint));
    }
    if (a.time_remap === false) { layer.timeRemapEnabled = false; }
    if (a.freeze_at !== null || a.remap_keys.length) {
        prop = remapProperty(layer);
        if (a.freeze_at !== null) {
            wanted.push({time: layer.inPoint, source_time: a.freeze_at}, {time: layer.outPoint, source_time: a.freeze_at});
        }
        for (i = 0; i < a.remap_keys.length; i++) { wanted.push(a.remap_keys[i]); }
        // Removing every key hides the property, so the new keys go in first and the old ones are dropped after.
        for (i = 0; i < wanted.length; i++) { prop.setValueAtTime(wanted[i].time, wanted[i].source_time); }
        for (i = prop.numKeys; i >= 1; i--) {
            if (!listed(wanted, prop.keyTime(i))) { prop.removeKey(i); }
        }
    } else if (a.time_remap === true) {
        remapProperty(layer);
    }
    if (a.frame_blending !== null) {
        layer.frameBlendingType = caviEnum(BLEND, a.frame_blending, "frame blending");
        if (a.frame_blending !== "none") { comp.frameBlending = true; }
    }
    if (layer.timeRemapEnabled) {
        prop = layer.property("ADBE Time Remapping");
        for (i = 1; i <= prop.numKeys; i++) { keys.push({time: prop.keyTime(i), source_time: prop.keyValue(i)}); }
    }
    caviReport({comp: comp.name, layer: layer.name, time_remap: layer.timeRemapEnabled, keys: keys, stretch: layer.stretch,
        in_point: layer.inPoint, out_point: layer.outPoint,
        visible_start: Math.min(layer.inPoint, layer.outPoint), visible_end: Math.max(layer.inPoint, layer.outPoint), frame_blending: String(layer.frameBlendingType),
        frame_blending_on: layer.frameBlending, comp_frame_blending: comp.frameBlending, errors: []});
})();
