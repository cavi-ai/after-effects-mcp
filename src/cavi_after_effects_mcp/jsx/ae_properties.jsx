$.evalFile(new File(CAVI_LIB));

var AT = null, KEYS = false, KEY_LIMIT = 1000;

// A value as JSON can carry it: a text document's text, "shape" and "marker" for those kinds, null for others.
function plainValue(prop, v) {
    if (prop.propertyValueType === PropertyValueType.NO_VALUE || prop.propertyValueType === PropertyValueType.CUSTOM_VALUE) { return null; }
    if (prop.propertyValueType === PropertyValueType.SHAPE) { return "shape"; }
    if (prop.propertyValueType === PropertyValueType.MARKER) { return "marker"; }
    if (prop.propertyValueType === PropertyValueType.TEXT_DOCUMENT) { return v.text; }
    if (typeof v === "object" && v !== null && v.length === undefined) { return null; }
    return v;
}

function plain(prop) {
    if (prop.propertyValueType === PropertyValueType.NO_VALUE || prop.propertyValueType === PropertyValueType.CUSTOM_VALUE) { return null; }
    return plainValue(prop, AT === null ? prop.value : prop.valueAtTime(AT, false));
}

function interpolation(type) {
    if (type === KeyframeInterpolationType.HOLD) { return "hold"; }
    return type === KeyframeInterpolationType.LINEAR ? "linear" : "bezier";
}

// The ease of the first dimension, as ae_keyframes takes it.
function ease(list) {
    return list && list.length ? {speed: list[0].speed, influence: list[0].influence} : null;
}

// Keys as {time, value, in_interpolation, out_interpolation, ease_in, ease_out}, with spatial tangents, continuity
// and roving on spatial properties.
function keyframes(prop) {
    var out = [], k, key, last = Math.min(prop.numKeys, KEY_LIMIT);
    for (k = 1; k <= last; k++) {
        key = {time: prop.keyTime(k), value: plainValue(prop, prop.keyValue(k)),
            in_interpolation: interpolation(prop.keyInInterpolationType(k)),
            out_interpolation: interpolation(prop.keyOutInterpolationType(k)), ease_in: null, ease_out: null};
        try {
            key.ease_in = ease(prop.keyInTemporalEase(k));
            key.ease_out = ease(prop.keyOutTemporalEase(k));
        } catch (noEase) { /* properties without temporal ease, such as Source Text */ }
        if (prop.isSpatial) {
            key.in_tangent = prop.keyInSpatialTangent(k);
            key.out_tangent = prop.keyOutSpatialTangent(k);
            key.spatial_continuous = prop.keySpatialContinuous(k);
            key.spatial_auto_bezier = prop.keySpatialAutoBezier(k);
            key.roving = prop.keyRoving(k);
        }
        out.push(key);
    }
    return out;
}

function node(prop, path) {
    var out = {path: path, name: prop.name, match_name: prop.matchName}, items;
    if (prop.propertyType === PropertyType.PROPERTY) {
        out.value = plain(prop);
        items = caviMenuItems(prop);
        if (items !== null) {
            out.items = items;
            out.text = AT === null ? prop.valueText : items[prop.valueAtTime(AT, false) - 1];
        }
        out.keys = prop.numKeys;
        out.expression = prop.canSetExpression && prop.expression !== "" ? prop.expression : null;
        if (KEYS && prop.numKeys > 0) {
            out.keyframes = keyframes(prop);
            out.keyframes_truncated = prop.numKeys > KEY_LIMIT;
        }
    }
    return out;
}

// The names from the layer down to prop, as a read of the whole tree reports them.
function groupPath(prop) {
    var names = [], p;
    for (p = prop; p.propertyDepth > 0; p = p.parentProperty) { names.unshift(p.name); }
    return names.join("/");
}

function walk(group, path, depth, out, a) {
    var i, child, childPath;
    for (i = 1; i <= group.numProperties && out.nodes.length < a.max_nodes; i++) {
        try {
            child = group.property(i);
            childPath = path + "/" + child.name;
            if (child.propertyType === PropertyType.PROPERTY) {
                out.nodes.push(node(child, childPath));
            } else if (depth > 1) {
                walk(child, childPath, depth - 1, out, a);
            }
        } catch (hidden) { continue; }
    }
}

(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), layer = caviLayer(comp, a.layer), root = layer, out = {nodes: []}, base = layer.name;
    AT = a.time;
    KEYS = a.keyframes;
    if (a.path !== null) {
        root = caviProp(layer, a.path);
        base = base + "/" + groupPath(root);
    }
    if (root.propertyType === PropertyType.PROPERTY) {
        out.nodes.push(node(root, base));
    } else {
        walk(root, base, a.depth, out, a);
    }
    caviReport({comp: comp.name, layer: layer.name, count: out.nodes.length, truncated: out.nodes.length >= a.max_nodes, properties: out.nodes, errors: []});
})();
