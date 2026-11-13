$.evalFile(new File(CAVI_LIB));

var CONTROLS = {slider: ["ADBE Slider Control", "Slider"], angle: ["ADBE Angle Control", "Angle"],
    point: ["ADBE Point Control", "Point"], point3d: ["ADBE Point3D Control", "3D Point"],
    color: ["ADBE Color Control", "Color"], checkbox: ["ADBE Checkbox Control", "Checkbox"],
    layer: ["ADBE Layer Control", "Layer"], dropdown: ["ADBE Dropdown Control", "Menu"]};

function addControl(layer, spec) {
    var kind = CONTROLS[spec.kind], effect, param, value = spec.value;
    if (!kind) { caviFail("Unknown control kind " + spec.kind); }
    var parade = layer.property("ADBE Effect Parade");
    effect = parade.addProperty(kind[0]);
    if (spec.kind === "dropdown" && spec.items.length) {
        // Setting the menu rebuilds the effect, so it is renamed afterwards from the end of the stack.
        effect.property(1).setPropertyParameters(spec.items);
        effect = parade.property(parade.numProperties);
    }
    effect.name = spec.name;
    param = effect.property(1);
    if (value !== null) {
        if (spec.kind === "checkbox") { value = value ? 1 : 0; }
        if (spec.kind === "layer") { value = caviLayer(layer.containingComp, value).index; }
        param.setValue(value);
    }
}

function control(layer, name) {
    var fx = layer.property("ADBE Effect Parade").property(name);
    if (!fx) { caviFail("Layer " + layer.name + " has no control named " + name); }
    return fx;
}

(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), host = caviLayer(comp, a.layer), i, spec, target, prop, expr, linked = [], names = [],
        fx, base, kind;
    for (i = 0; i < a.controls.length; i++) { addControl(host, a.controls[i]); }
    for (i = 0; i < a.links.length; i++) {
        spec = a.links[i];
        fx = control(host, spec.control);
        kind = null;
        for (target in CONTROLS) { if (CONTROLS.hasOwnProperty(target) && CONTROLS[target][1] === fx.property(1).name) { kind = CONTROLS[target]; } }
        base = 'thisComp.layer("' + host.name.replace(/"/g, '\\"') + '").effect("' + spec.control.replace(/"/g, '\\"') + '")("' + kind[1] + '")';
        expr = base;
        if (spec.scale !== 1) { expr = "(" + expr + ") * " + spec.scale; }
        if (spec.offset !== 0) { expr = "(" + expr + ") + " + spec.offset; }
        if (spec.axis !== null) {
            expr = "v = value;\nv[" + {x: 0, y: 1, z: 2}[spec.axis] + "] = " + expr + ";\nv";
        }
        target = caviLayer(comp, spec.layer === null ? a.layer : spec.layer);
        prop = caviProp(target, spec.property);
        prop.expression = expr;
        if (prop.expressionError) { caviFail("Expression error on " + target.name + " " + spec.property + ": " + prop.expressionError); }
        linked.push({layer: target.name, property: spec.property, expression: expr});
    }
    fx = host.property("ADBE Effect Parade");
    for (i = 1; i <= fx.numProperties; i++) { names.push(fx.property(i).name); }
    caviReport({comp: comp.name, layer: host.name, controls: names, links: linked, errors: []});
})();
