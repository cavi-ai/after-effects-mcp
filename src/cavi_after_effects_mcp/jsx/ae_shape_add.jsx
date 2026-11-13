$.evalFile(new File(CAVI_LIB));

function put(group, match, value) {
    if (value !== null && value !== undefined) { group.property(match).setValue(value); }
}

function pathShape(spec) {
    var shape = new Shape();
    shape.vertices = spec.vertices;
    shape.inTangents = spec.in_tangents;
    shape.outTangents = spec.out_tangents;
    shape.closed = spec.closed;
    return shape;
}

function primitive(contents, s) {
    var item;
    if (s.kind === "rect") {
        item = contents.addProperty("ADBE Vector Shape - Rect");
        put(item, "ADBE Vector Rect Size", s.size);
        put(item, "ADBE Vector Rect Position", s.position);
        put(item, "ADBE Vector Rect Roundness", s.roundness);
    } else if (s.kind === "ellipse") {
        item = contents.addProperty("ADBE Vector Shape - Ellipse");
        put(item, "ADBE Vector Ellipse Size", s.size);
        put(item, "ADBE Vector Ellipse Position", s.position);
    } else if (s.kind === "polystar") {
        item = contents.addProperty("ADBE Vector Shape - Star");
        put(item, "ADBE Vector Star Type", s.star ? 1 : 2);
        put(item, "ADBE Vector Star Points", s.points);
        put(item, "ADBE Vector Star Position", s.position);
        put(item, "ADBE Vector Star Rotation", s.rotation);
        put(item, "ADBE Vector Star Outer Radius", s.outer_radius);
        if (s.star) { put(item, "ADBE Vector Star Inner Radius", s.inner_radius); }
        put(item, "ADBE Vector Star Outer Roundess", s.outer_roundness);
        if (s.star) { put(item, "ADBE Vector Star Inner Roundess", s.inner_roundness); }
    } else if (s.kind === "path") {
        item = contents.addProperty("ADBE Vector Shape - Group");
        item.property("ADBE Vector Shape").setValue(pathShape(s));
    } else {
        caviFail("Unknown shape kind " + s.kind);
    }
}

function paint(contents, a) {
    var item, i, dash;
    if (a.gradient_fill) {
        item = contents.addProperty("ADBE Vector Graphic - G-Fill");
        put(item, "ADBE Vector Grad Type", a.gradient_fill.type === "radial" ? 2 : 1);
        put(item, "ADBE Vector Grad Start Pt", a.gradient_fill.start);
        put(item, "ADBE Vector Grad End Pt", a.gradient_fill.end);
        put(item, "ADBE Vector Fill Opacity", a.gradient_fill.opacity);
    }
    if (a.gradient_stroke) {
        item = contents.addProperty("ADBE Vector Graphic - G-Stroke");
        put(item, "ADBE Vector Grad Type", a.gradient_stroke.type === "radial" ? 2 : 1);
        put(item, "ADBE Vector Grad Start Pt", a.gradient_stroke.start);
        put(item, "ADBE Vector Grad End Pt", a.gradient_stroke.end);
        put(item, "ADBE Vector Stroke Width", a.gradient_stroke.width);
    }
    if (a.stroke) {
        item = contents.addProperty("ADBE Vector Graphic - Stroke");
        put(item, "ADBE Vector Stroke Color", a.stroke.color);
        put(item, "ADBE Vector Stroke Width", a.stroke.width);
        put(item, "ADBE Vector Stroke Opacity", a.stroke.opacity);
        put(item, "ADBE Vector Stroke Line Cap", caviEnum({BUTT: 1, ROUND: 2, SQUARE: 3}, a.stroke.cap, "line cap"));
        put(item, "ADBE Vector Stroke Line Join", caviEnum({MITER: 1, ROUND: 2, BEVEL: 3}, a.stroke.join, "line join"));
        for (i = 0; i < a.stroke.dashes.length && i < 6; i++) {
            dash = i % 2 === 0 ? "ADBE Vector Stroke Dash " + (i / 2 + 1) : "ADBE Vector Stroke Gap " + ((i + 1) / 2);
            item.property("ADBE Vector Stroke Dashes").addProperty(dash).setValue(a.stroke.dashes[i]);
        }
    }
    if (a.fill) {
        item = contents.addProperty("ADBE Vector Graphic - Fill");
        put(item, "ADBE Vector Fill Color", a.fill.color);
        put(item, "ADBE Vector Fill Opacity", a.fill.opacity);
    }
}

function operator(contents, o) {
    var item, xf;
    if (o.type === "trim") {
        item = contents.addProperty("ADBE Vector Filter - Trim");
        put(item, "ADBE Vector Trim Start", o.start);
        put(item, "ADBE Vector Trim End", o.end);
        put(item, "ADBE Vector Trim Offset", o.offset);
        put(item, "ADBE Vector Trim Type", o.individually ? 2 : 1);
    } else if (o.type === "repeater") {
        item = contents.addProperty("ADBE Vector Filter - Repeater");
        put(item, "ADBE Vector Repeater Copies", o.copies);
        put(item, "ADBE Vector Repeater Offset", o.offset);
        xf = item.property("ADBE Vector Repeater Transform");
        put(xf, "ADBE Vector Repeater Anchor", o.anchor);
        put(xf, "ADBE Vector Repeater Position", o.position);
        put(xf, "ADBE Vector Repeater Scale", o.scale);
        put(xf, "ADBE Vector Repeater Rotation", o.rotation);
        put(xf, "ADBE Vector Repeater Opacity 1", o.start_opacity);
        put(xf, "ADBE Vector Repeater Opacity 2", o.end_opacity);
    } else if (o.type === "round_corners") {
        put(contents.addProperty("ADBE Vector Filter - RC"), "ADBE Vector RoundCorner Radius", o.radius);
    } else if (o.type === "offset") {
        item = contents.addProperty("ADBE Vector Filter - Offset");
        put(item, "ADBE Vector Offset Amount", o.amount);
        put(item, "ADBE Vector Offset Line Join", o.join === null ? null : caviEnum({MITER: 1, ROUND: 2, BEVEL: 3}, o.join, "line join"));
        put(item, "ADBE Vector Offset Miter Limit", o.miter_limit);
    } else if (o.type === "wiggle") {
        item = contents.addProperty("ADBE Vector Filter - Roughen");
        put(item, "ADBE Vector Roughen Size", o.size);
        put(item, "ADBE Vector Roughen Detail", o.detail);
        put(item, "ADBE Vector Roughen Points", o.smooth ? 2 : 1);
        put(item, "ADBE Vector Temporal Freq", o.speed);
        put(item, "ADBE Vector Correlation", o.correlation);
        put(item, "ADBE Vector Random Seed", o.seed);
    } else if (o.type === "merge") {
        put(contents.addProperty("ADBE Vector Filter - Merge"), "ADBE Vector Merge Type",
            caviEnum({MERGE: 1, ADD: 2, SUBTRACT: 3, INTERSECT: 4, EXCLUDE: 5}, o.mode, "merge mode"));
    } else {
        caviFail("Unknown operator " + o.type);
    }
}

(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), layer, group, contents, i, xf, t = a.transform, names = [];
    if (a.layer !== null) {
        layer = caviLayer(comp, a.layer);
        if (!(layer instanceof ShapeLayer)) { caviFail("Layer " + layer.name + " is not a shape layer"); }
    } else {
        layer = comp.layers.addShape();
        layer.name = a.name;
        // The layer sits at the comp origin, so group positions are comp pixels.
        layer.property("ADBE Transform Group").property("ADBE Position").setValue([0, 0]);
    }
    group = layer.property("ADBE Root Vectors Group").addProperty("ADBE Vector Group");
    group.name = a.group_name;
    contents = group.property("ADBE Vectors Group");
    primitive(contents, a.shape);
    for (i = 0; i < a.operators.length; i++) {
        if (a.operators[i].type !== "repeater") { operator(contents, a.operators[i]); }
    }
    paint(contents, a);
    for (i = 0; i < a.operators.length; i++) {
        if (a.operators[i].type === "repeater") { operator(contents, a.operators[i]); }
    }
    xf = group.property("ADBE Vector Transform Group");
    put(xf, "ADBE Vector Anchor", t.anchor);
    put(xf, "ADBE Vector Position", t.position);
    put(xf, "ADBE Vector Scale", t.scale);
    put(xf, "ADBE Vector Rotation", t.rotation);
    put(xf, "ADBE Vector Group Opacity", t.opacity);
    for (i = 1; i <= contents.numProperties; i++) { names.push(contents.property(i).matchName); }
    caviReport({comp: comp.name, layer: describeLayer(layer), group: group.name, contents: names, errors: []});
})();
