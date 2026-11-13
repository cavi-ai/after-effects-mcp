$.evalFile(new File(CAVI_LIB));

function maskShape(spec) {
    var shape = new Shape();
    shape.vertices = spec.vertices;
    shape.inTangents = spec.in_tangents;
    shape.outTangents = spec.out_tangents;
    shape.closed = spec.closed;
    return shape;
}

function maskByRef(parade, ref) {
    var i;
    if (typeof ref === "number") {
        if (ref < 1 || ref > parade.numProperties) { caviFail("The layer has no mask " + ref); }
        return parade.property(ref);
    }
    for (i = 1; i <= parade.numProperties; i++) {
        if (parade.property(i).name === ref) { return parade.property(i); }
    }
    return caviFail("The layer has no mask named " + ref);
}

(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), layer = caviLayer(comp, a.layer), parade = layer.property("ADBE Mask Parade"),
        mask, path, i, modes = {NONE: MaskMode.NONE, ADD: MaskMode.ADD, SUBTRACT: MaskMode.SUBTRACT,
            INTERSECT: MaskMode.INTERSECT, LIGHTEN: MaskMode.LIGHTEN, DARKEN: MaskMode.DARKEN,
            DIFFERENCE: MaskMode.DIFFERENCE};
    if (a.mask !== null) {
        mask = maskByRef(parade, a.mask);
    } else {
        mask = parade.addProperty("ADBE Mask Atom");
    }
    if (a.name !== null) { mask.name = a.name; }
    path = mask.property("ADBE Mask Shape");
    if (a.shape !== null) { path.setValue(maskShape(a.shape)); }
    for (i = 0; i < a.path_keys.length; i++) {
        path.setValueAtTime(a.path_keys[i].time, maskShape(a.path_keys[i].shape));
    }
    if (a.mode !== null) { mask.maskMode = caviEnum(modes, a.mode, "mask mode"); }
    if (a.feather !== null) { mask.property("ADBE Mask Feather").setValue(a.feather); }
    if (a.expansion !== null) { mask.property("ADBE Mask Offset").setValue(a.expansion); }
    if (a.opacity !== null) { mask.property("ADBE Mask Opacity").setValue(a.opacity); }
    if (a.invert !== null) { mask.inverted = a.invert; }
    caviReport({comp: comp.name, layer: layer.name, mask: mask.name, index: mask.propertyIndex, mask_count: parade.numProperties,
        mode: String(mask.maskMode), inverted: mask.inverted, feather: mask.property("ADBE Mask Feather").value,
        expansion: mask.property("ADBE Mask Offset").value, opacity: mask.property("ADBE Mask Opacity").value,
        path_keys: path.numKeys, vertices: path.value.vertices.length, errors: []});
})();
