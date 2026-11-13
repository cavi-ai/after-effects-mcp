$.evalFile(new File(CAVI_LIB));

(function () {
    var a = CAVI_ARGS, list = [], i, e, text = String(a.filter).toLowerCase(), total = 0, cats = {};
    for (i = 0; i < app.effects.length; i++) {
        e = app.effects[i];
        if (a.category !== null && e.category !== a.category) { continue; }
        if (text !== "" && (e.displayName + " " + e.matchName + " " + e.category).toLowerCase().indexOf(text) < 0) { continue; }
        total++;
        cats[e.category] = (cats[e.category] || 0) + 1;
        if (list.length < a.limit) {
            list.push({category: e.category, name: e.displayName, match_name: e.matchName});
        }
    }
    caviReport({effects: list, total: total, categories: cats, errors: []});
})();
