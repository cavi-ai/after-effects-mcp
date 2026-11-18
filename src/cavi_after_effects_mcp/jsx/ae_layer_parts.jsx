$.evalFile(new File(CAVI_LIB));

// The path of a property from its layer, by display names.
function pathOf(prop) {
    var names = [];
    while (prop.parentProperty !== null) {
        names.unshift(prop.name);
        prop = prop.parentProperty;
    }
    return names.join("/");
}

function members(group) {
    var out = [], i, child;
    for (i = 1; i <= group.numProperties; i++) {
        child = group.property(i);
        out.push({index: i, name: child.name, match_name: child.matchName, enabled: child.enabled});
    }
    return out;
}

(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), layer = caviLayer(comp, a.layer), i, e, prop, parent, where,
        touched = [], seen = {}, groups = {};
    for (i = 0; i < a.edits.length; i++) {
        e = a.edits[i];
        prop = caviProp(layer, e.path);
        parent = prop.parentProperty;
        if (prop.propertyType === PropertyType.PROPERTY || parent === null || parent.propertyType !== PropertyType.INDEXED_GROUP) {
            caviFail(e.path + " on layer " + layer.name + " is not an effect, mask, shape group or text animator");
        }
        where = pathOf(parent);
        if (!seen[where]) {
            seen[where] = true;
            touched.push(where);
        }
        if (e.action === "remove") {
            prop.remove();
        } else if (e.action === "move") {
            if (e.to > parent.numProperties) {
                caviFail(e.path + " cannot move to " + e.to + "; " + where + " has " + parent.numProperties);
            }
            prop.moveTo(e.to);
        } else {
            if (!prop.canSetEnabled) { caviFail(e.path + " on layer " + layer.name + " has no on/off switch"); }
            prop.enabled = e.action === "enable";
        }
    }
    // Paths are looked up again: moving a property invalidates references to its group's members.
    for (i = 0; i < touched.length; i++) {
        groups[touched[i]] = members(caviProp(layer, touched[i]));
    }
    caviReport({comp: comp.name, layer: layer.name, groups: groups, errors: []});
})();
