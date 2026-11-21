$.evalFile(new File(CAVI_LIB));

function refuseFlat(layer) {
    if (layer instanceof CameraLayer) { caviFail("Layer " + layer.name + " is a camera"); }
    if (layer instanceof LightLayer) { caviFail("Layer " + layer.name + " is a light"); }
    if (layer.threeDLayer === true) { caviFail("Layer " + layer.name + " is 3D"); }
    if (layer.locked) { caviFail("Layer " + layer.name + " is locked"); }
}

function belowZero(time) {
    return time < -0.0000001;
}

function shiftSpan(layer, offset) {
    var start = layer.startTime, inn = layer.inPoint, out = layer.outPoint;
    layer.startTime = start + offset;
    if (Math.abs(layer.startTime - (start + offset)) > 0.0000001) {
        caviFail("Layer " + layer.name + " start time could not move by the requested offset");
    }
    layer.inPoint = inn + offset;
    layer.outPoint = out + offset;
}

function keyedProperties(group, found) {
    var i, prop;
    for (i = 1; i <= group.numProperties; i++) {
        try { prop = group.property(i); } catch (hidden) { continue; }
        if (!prop) { continue; }
        if (prop.propertyType === PropertyType.PROPERTY) {
            if (prop.numKeys > 0) { found.push(prop); }
        } else {
            keyedProperties(prop, found);
        }
    }
    return found;
}

function refuseKeys(layer, props, offset) {
    var p, i, time;
    for (p = 0; p < props.length; p++) {
        for (i = 1; i <= props[p].numKeys; i++) {
            time = props[p].keyTime(i) + offset;
            if (belowZero(time)) {
                caviFail("Layer " + layer.name + " key on " + props[p].name + " would move below 0");
            }
        }
    }
}

function hasSetKeyTime(prop) {
    var kind;
    try { kind = typeof prop.setKeyTime; } catch (missing) { return false; }
    return kind === "function";
}

function captureKey(prop, index) {
    var snap = {time: prop.keyTime(index), value: prop.keyValue(index), roving: false, inType: null, outType: null,
        inEase: null, outEase: null, inTan: null, outTan: null, continuous: null, auto: null}, spatial = false;
    try { snap.inType = prop.keyInInterpolationType(index); } catch (noIn) {}
    try { snap.outType = prop.keyOutInterpolationType(index); } catch (noOut) {}
    try {
        snap.inEase = prop.keyInTemporalEase(index);
        snap.outEase = prop.keyOutTemporalEase(index);
    } catch (noEase) {}
    try { spatial = prop.isSpatial; } catch (noSpatial) { spatial = false; }
    if (spatial) {
        try {
            snap.inTan = prop.keyInSpatialTangent(index);
            snap.outTan = prop.keyOutSpatialTangent(index);
        } catch (noTan) {}
        try { snap.continuous = prop.keySpatialContinuous(index); } catch (noCont) {}
        try { snap.auto = prop.keySpatialAutoBezier(index); } catch (noAuto) {}
    }
    try { snap.roving = prop.keyRoving(index); } catch (noRove) {}
    return snap;
}

function placeKey(prop, snap, offset) {
    var time = snap.time + offset, at;
    prop.setValueAtTime(time, snap.value);
    at = prop.nearestKeyIndex(time);
    if (snap.inType !== null && snap.outType !== null) {
        try { prop.setInterpolationTypeAtKey(at, snap.inType, snap.outType); } catch (noType) {}
    }
    if (snap.inEase !== null && snap.outEase !== null) {
        try { prop.setTemporalEaseAtKey(at, snap.inEase, snap.outEase); } catch (noEase) {}
    }
    if (snap.inTan !== null && snap.outTan !== null) {
        try { prop.setSpatialTangentsAtKey(at, snap.inTan, snap.outTan); } catch (noTan) {}
        if (snap.auto !== null) {
            try { prop.setSpatialAutoBezierAtKey(at, snap.auto); } catch (noAuto) {}
        }
        if (snap.continuous !== null) {
            try { prop.setSpatialContinuousAtKey(at, snap.continuous); } catch (noCont) {}
        }
    }
}

function recreateKeys(prop, offset) {
    var n = prop.numKeys, saved = [], i, at;
    for (i = 1; i <= n; i++) { saved.push(captureKey(prop, i)); }
    for (i = n; i >= 1; i--) { prop.removeKey(i); }
    if (offset > 0) {
        for (i = saved.length - 1; i >= 0; i--) { placeKey(prop, saved[i], offset); }
    } else {
        for (i = 0; i < saved.length; i++) { placeKey(prop, saved[i], offset); }
    }
    for (i = 0; i < saved.length; i++) {
        if (saved[i].roving) {
            at = prop.nearestKeyIndex(saved[i].time + offset);
            try { prop.setRovingAtKey(at, true); } catch (noRove) {}
        }
    }
}

function shiftProperty(prop, offset) {
    var n = prop.numKeys, i, moved = 0;
    if (n === 0 || offset === 0) { return 0; }
    if (hasSetKeyTime(prop)) {
        try {
            if (offset > 0) {
                for (i = n; i >= 1; i--) {
                    prop.setKeyTime(i, prop.keyTime(i) + offset);
                    moved++;
                }
            } else {
                for (i = 1; i <= n; i++) {
                    prop.setKeyTime(i, prop.keyTime(i) + offset);
                    moved++;
                }
            }
            return n;
        } catch (failed) {
            if (moved > 0) { throw failed; }
        }
    }
    recreateKeys(prop, offset);
    return n;
}

(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), layers = [], report = [], i, layer, offset, props, keys, p, span, keyed;
    if (a.mode !== "in_points" && a.mode !== "keyframes" && a.mode !== "both") {
        caviFail("Unknown mode " + a.mode);
    }
    for (i = 0; i < a.layers.length; i++) {
        layer = caviLayer(comp, a.layers[i]);
        refuseFlat(layer);
        layers.push(layer);
    }
    for (i = 0; i < layers.length; i++) {
        layer = layers[i];
        offset = i * a.frames * comp.frameDuration;
        span = a.mode === "in_points" || a.mode === "both";
        keyed = a.mode === "keyframes" || a.mode === "both";
        props = keyedProperties(layer, []);
        if (span && offset !== 0 && belowZero(layer.inPoint + offset)) {
            caviFail("Layer " + layer.name + " in point would move below 0");
        }
        if (keyed && offset !== 0) { refuseKeys(layer, props, offset); }
        keys = 0;
        if (offset !== 0 && span) { shiftSpan(layer, offset); }
        if (offset !== 0) {
            for (p = 0; p < props.length; p++) {
                if (a.mode === "both") { keys += props[p].numKeys; }
                else if (a.mode === "keyframes") { keys += shiftProperty(props[p], offset); }
                else { shiftProperty(props[p], -offset); }
            }
        }
        report.push({layer: layer.name, index: layer.index, offset: offset, in_point: layer.inPoint,
            out_point: layer.outPoint, keys: keys});
    }
    caviReport({comp: comp.name, mode: a.mode, layers: report, errors: []});
})();
