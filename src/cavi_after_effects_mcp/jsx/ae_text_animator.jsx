$.evalFile(new File(CAVI_LIB));

var MATCH = {opacity: "ADBE Text Opacity", position: "ADBE Text Position 3D", tracking: "ADBE Text Tracking Amount",
    scale: "ADBE Text Scale 3D", blur: "ADBE Text Blur", rotation: "ADBE Text Rotation", fill_color: "ADBE Text Fill Color",
    stroke_color: "ADBE Text Stroke Color", stroke_width: "ADBE Text Stroke Width", skew: "ADBE Text Skew",
    skew_axis: "ADBE Text Skew Axis", character_offset: "ADBE Text Character Offset", rotation_x: "ADBE Text Rotation X",
    rotation_y: "ADBE Text Rotation Y"};
var UNITS = {CHARACTERS: 1, CHARACTERS_NO_SPACES: 2, WORDS: 3, LINES: 4};
var SHAPES = {SQUARE: 1, RAMP_UP: 2, RAMP_DOWN: 3, TRIANGLE: 4, ROUND: 5, SMOOTH: 6};

// Adding a property invalidates earlier references to its siblings, so animators are fetched by index each time
// and a new property is used straight from addProperty.
function animatorAt(layer, index) {
    return layer.property("ADBE Text Properties").property("ADBE Text Animators").property(index);
}

function put(group, match, value) {
    if (value !== null && value !== undefined) { group.property(match).setValue(value); }
}

function addSelector(layer, animator, s) {
    var sels = animatorAt(layer, animator).property("ADBE Text Selectors"), kind = {range: "ADBE Text Selector",
        wiggly: "ADBE Text Wiggly Selector", expression: "ADBE Text Expressible Selector"}[s.kind], sel, adv, a;
    sel = sels.addProperty(kind);
    if (s.kind === "range") {
        adv = sel.property("ADBE Text Range Advanced");
        put(adv, "ADBE Text Range Type2", caviEnum(UNITS, s.unit, "unit"));
        put(sel, "ADBE Text Percent Start", s.start);
        put(sel, "ADBE Text Percent End", s.end);
        put(sel, "ADBE Text Percent Offset", s.offset);
        if (s.shape !== null) { put(adv, "ADBE Text Range Shape", caviEnum(SHAPES, s.shape, "shape")); }
        put(adv, "ADBE Text Levels Max Ease", s.ease_high);
        put(adv, "ADBE Text Levels Min Ease", s.ease_low);
        put(adv, "ADBE Text Selector Smoothness", s.smoothness);
        if (s.animate !== null) {
            a = s.animate;
            caviKeys(sel.property("ADBE Text Percent Start"),
                [{time: a.start, value: 0, ease_in: null, ease_out: null, interpolation: null},
                 {time: a.start + a.duration, value: 100, ease_in: null, ease_out: null, interpolation: null}], a.ease);
        }
    } else if (s.kind === "wiggly") {
        put(sel, "ADBE Text Range Type2", caviEnum(UNITS, s.unit, "unit"));
        put(sel, "ADBE Text Wiggly Max Amount", s.max_amount);
        put(sel, "ADBE Text Wiggly Min Amount", s.min_amount);
        put(sel, "ADBE Text Temporal Freq", s.per_second);
        put(sel, "ADBE Text Character Correlation", s.correlation);
        put(sel, "ADBE Text Wiggly Random Seed", s.seed);
    } else {
        put(sel, "ADBE Text Range Type2", caviEnum(UNITS, s.unit, "unit"));
        if (s.amount !== null) {
            sel.property("ADBE Text Expressible Amount").expression = s.amount;
            if (sel.property("ADBE Text Expressible Amount").expressionError) {
                caviFail("Expression error: " + sel.property("ADBE Text Expressible Amount").expressionError);
            }
        }
    }
}

function maskIndex(layer, ref) {
    var parade = layer.property("ADBE Mask Parade"), i;
    if (typeof ref === "number") { return ref; }
    for (i = 1; i <= parade.numProperties; i++) {
        if (parade.property(i).name === ref) { return i; }
    }
    return caviFail("The layer has no mask named " + ref);
}

(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), layer = caviLayer(comp, a.layer), i, j, spec, index, name, value, report = [], opts;
    if (!(layer instanceof TextLayer)) {
        caviFail("Layer " + layer.name + " is not a text layer");
    }
    for (i = 0; i < a.animators.length; i++) {
        spec = a.animators[i];
        layer.property("ADBE Text Properties").property("ADBE Text Animators").addProperty("ADBE Text Animator");
        index = layer.property("ADBE Text Properties").property("ADBE Text Animators").numProperties;
        if (spec.name) { animatorAt(layer, index).name = spec.name; }
        for (name in spec.properties) {
            if (spec.properties.hasOwnProperty(name) && spec.properties[name] !== null) {
                value = spec.properties[name];
                if (name === "position" && value.length === 2) { value = [value[0], value[1], 0]; }
                if (name === "scale" && value.length === 2) { value = [value[0], value[1], 100]; }
                animatorAt(layer, index).property("ADBE Text Animator Properties").addProperty(MATCH[name]).setValue(value);
            }
        }
        for (j = 0; j < spec.selectors.length; j++) { addSelector(layer, index, spec.selectors[j]); }
        report.push({name: animatorAt(layer, index).name, selectors: animatorAt(layer, index).property("ADBE Text Selectors").numProperties});
    }
    if (a.path !== null) {
        opts = layer.property("ADBE Text Properties").property("ADBE Text Path Options");
        put(opts, "ADBE Text Path", maskIndex(layer, a.path.mask));
        put(opts, "ADBE Text First Margin", a.path.first_margin);
        put(opts, "ADBE Text Last Margin", a.path.last_margin);
        put(opts, "ADBE Text Reverse Path", a.path.reverse ? 1 : 0);
        put(opts, "ADBE Text Perpendicular To Path", a.path.perpendicular ? 1 : 0);
        put(opts, "ADBE Text Force Align Path", a.path.force_align ? 1 : 0);
    }
    caviReport({comp: comp.name, layer: layer.name, animators: report, path: a.path !== null ? opts.property("ADBE Text Path").value : null,
        animator_count: layer.property("ADBE Text Properties").property("ADBE Text Animators").numProperties, errors: []});
})();
