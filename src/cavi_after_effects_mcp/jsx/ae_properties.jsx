$.evalFile(new File(CAVI_LIB));

function plain(prop) {
    var v;
    if (prop.propertyValueType === PropertyValueType.NO_VALUE || prop.propertyValueType === PropertyValueType.CUSTOM_VALUE) { return null; }
    if (prop.propertyValueType === PropertyValueType.SHAPE) { return "shape"; }
    if (prop.propertyValueType === PropertyValueType.MARKER) { return "marker"; }
    v = prop.value;
    if (prop.propertyValueType === PropertyValueType.TEXT_DOCUMENT) { return v.text; }
    if (typeof v === "object" && v !== null && v.length === undefined) { return null; }
    return v;
}

function node(prop, path) {
    var out = {path: path, name: prop.name, match_name: prop.matchName};
    if (prop.propertyType === PropertyType.PROPERTY) {
        out.value = plain(prop);
        out.keys = prop.numKeys;
        out.expression = prop.canSetExpression && prop.expression !== "" ? prop.expression : null;
    }
    return out;
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
    if (a.path !== null) {
        root = caviProp(layer, a.path);
        base = base + "/" + root.name;
    }
    if (root.propertyType === PropertyType.PROPERTY) {
        out.nodes.push(node(root, base));
    } else {
        walk(root, base, a.depth, out, a);
    }
    caviReport({comp: comp.name, layer: layer.name, count: out.nodes.length, truncated: out.nodes.length >= a.max_nodes, properties: out.nodes, errors: []});
})();
