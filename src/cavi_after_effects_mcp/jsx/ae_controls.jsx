$.evalFile(new File(CAVI_LIB));

var CONTROLS = {slider: "ADBE Slider Control", angle: "ADBE Angle Control", point: "ADBE Point Control",
    point3d: "ADBE Point3D Control", color: "ADBE Color Control", checkbox: "ADBE Checkbox Control",
    layer: "ADBE Layer Control", dropdown: "ADBE Dropdown Control"};

function addControl(layer, spec) {
    var kind = CONTROLS[spec.kind], effect, param, value = spec.value;
    if (!kind) { caviFail("Unknown control kind " + spec.kind); }
    var parade = layer.property("ADBE Effect Parade");
    effect = parade.addProperty(kind);
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
        if (spec.kind === "dropdown") { value = caviMenuValue(param, value); }
        param.setValue(value);
    }
}

// The expression control named ``name`` on ``layer``, recognized by its match name in any language. A dropdown
// whose menu was set is rebuilt as a "Pseudo/@@..." effect; its first parameter is a dropdown.
function control(layer, name) {
    var fx = layer.property("ADBE Effect Parade").property(name), kind;
    if (!fx) { caviFail("Layer " + layer.name + " has no control named " + name); }
    for (kind in CONTROLS) {
        if (CONTROLS.hasOwnProperty(kind) && CONTROLS[kind] === fx.matchName) { return fx; }
    }
    if (fx.numProperties && fx.property(1).isDropdownEffect === true) { return fx; }
    return caviFail("Effect " + name + " on layer " + layer.name + " is " + fx.matchName + ", not an expression control");
}

(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), host = caviLayer(comp, a.layer), i, spec, target, prop, expr, linked = [], names = [],
        fx;
    if (a.controls.length) { caviGuard3D(comp, host, "an Expression Control"); }
    for (i = 0; i < a.controls.length; i++) { addControl(host, a.controls[i]); }
    for (i = 0; i < a.links.length; i++) {
        spec = a.links[i];
        control(host, spec.control);
        // The control's one parameter by index, since its display name is translated on other installs.
        expr = 'thisComp.layer("' + host.name.replace(/"/g, '\\"') + '").effect("' + spec.control.replace(/"/g, '\\"') + '")(1)';
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
