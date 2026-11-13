// Search and filters on the index, transposing on a chart. Every page reads
// without this file; it only adds the controls.
(function () {
  "use strict";

  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  };
  var each = function (list, fn) { Array.prototype.forEach.call(list, fn); };

  function norm(s) {
    return (s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "")
      .replace(/[^a-z0-9 ]+/g, " ").replace(/\s+/g, " ").trim();
  }

  // The index
  var finder = document.querySelector("[data-finder]");
  if (finder) {
    var input = finder.querySelector("[data-q]");
    var kindChips = finder.querySelectorAll("[data-kind-chip]");
    var keyChips = finder.querySelectorAll("[data-key-chip]");
    var rows = Array.prototype.slice.call(document.querySelectorAll(".list > li"));
    var groups = Array.prototype.slice.call(document.querySelectorAll(".group"));
    var empty = document.querySelector("[data-empty]");
    var rail = document.querySelector("[data-az]");
    var thumbs = {};
    each(rail.querySelectorAll("[data-thumb]"), function (a) { thumbs[a.getAttribute("data-thumb")] = a; });
    var state = { kind: "", key: "" };
    var lyrics = null;
    var loading = false;

    function loadLyrics() {
      if (lyrics || loading) return;
      loading = true;
      fetch("search.json").then(function (r) { return r.json(); }).then(function (data) {
        lyrics = {};
        Object.keys(data).forEach(function (k) { lyrics[k] = norm(data[k]); });
        apply();
      }).catch(function () { loading = false; });
    }

    function press(list, attr, value) {
      each(list, function (b) { b.setAttribute("aria-pressed", b.getAttribute(attr) === value ? "true" : "false"); });
    }

    function apply() {
      var q = norm(input.value);
      var words = q ? q.split(" ") : [];
      var shown = 0;
      rows.forEach(function (row) {
        var hay = row.getAttribute("data-q");
        var lyr = lyrics && lyrics[row.getAttribute("data-id")];
        if (lyr) hay += " " + lyr;
        var ok = words.every(function (w) { return hay.indexOf(w) !== -1; });
        if (ok && state.kind) ok = row.getAttribute("data-kind").split(" ").indexOf(state.kind) !== -1;
        if (ok && state.key) ok = row.getAttribute("data-key") === state.key;
        row.hidden = !ok;
        if (ok) shown++;
      });
      groups.forEach(function (g) {
        var any = g.querySelector("li:not([hidden])");
        g.hidden = !any;
        var t = thumbs[g.getAttribute("data-letter")];
        if (t) t.classList.toggle("dim", !any);
      });
      empty.hidden = shown !== 0;
      press(kindChips, "data-kind-chip", state.kind);
      press(keyChips, "data-key-chip", state.key);

      var params = new URLSearchParams();
      if (input.value.trim()) params.set("q", input.value.trim());
      if (state.kind) params.set("show", state.kind);
      if (state.key) params.set("key", state.key);
      var qs = params.toString();
      history.replaceState(null, "", qs ? "?" + qs : location.pathname);
    }

    var initial = new URLSearchParams(location.search);
    if (initial.get("q")) { input.value = initial.get("q"); loadLyrics(); }
    state.kind = initial.get("show") || "";
    state.key = initial.get("key") || "";
    if (initial.toString()) apply();

    input.addEventListener("input", function () { loadLyrics(); apply(); });
    input.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { input.value = ""; apply(); }
    });
    each(kindChips, function (b) {
      b.addEventListener("click", function () { state.kind = b.getAttribute("data-kind-chip"); apply(); });
    });
    each(keyChips, function (b) {
      b.addEventListener("click", function () {
        var k = b.getAttribute("data-key-chip");
        state.key = state.key === k ? "" : k;
        apply();
      });
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "/" && document.activeElement !== input && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        input.focus();
      }
    });

    // Drag a finger down the letters and the list follows, as in a phone's contacts.
    var scrubbing = false;
    function jumpTo(x, y) {
      var el = document.elementFromPoint(x, y);
      var a = el && el.closest && el.closest("[data-thumb]");
      if (!a || a.classList.contains("dim")) return;
      var g = document.getElementById("letter-" + a.getAttribute("data-thumb"));
      if (g) g.scrollIntoView({ block: "start" });
    }
    rail.addEventListener("pointerdown", function (e) {
      scrubbing = true;
      rail.setPointerCapture(e.pointerId);
      jumpTo(e.clientX, e.clientY);
      e.preventDefault();
    });
    rail.addEventListener("pointermove", function (e) { if (scrubbing) jumpTo(e.clientX, e.clientY); });
    rail.addEventListener("pointerup", function () { scrubbing = false; });
    rail.addEventListener("pointercancel", function () { scrubbing = false; });
    rail.addEventListener("click", function (e) { e.preventDefault(); });

    if ("IntersectionObserver" in window) {
      var current = null;
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (!en.isIntersecting) return;
          var l = en.target.getAttribute("data-letter");
          if (current && thumbs[current]) thumbs[current].removeAttribute("aria-current");
          current = l;
          if (thumbs[l]) thumbs[l].setAttribute("aria-current", "true");
        });
      }, { rootMargin: "-30% 0px -65% 0px" });
      groups.forEach(function (g) { io.observe(g); });
    }

    // The title of the song tapped is the one that travels into the next page.
    document.addEventListener("click", function (e) {
      var a = e.target.closest && e.target.closest(".row");
      if (!a) return;
      each(document.querySelectorAll(".row-title"), function (t) { t.style.viewTransitionName = ""; });
      a.querySelector(".row-title").style.viewTransitionName = "song-title";
    });
    window.addEventListener("pageshow", function () {
      each(document.querySelectorAll(".row-title"), function (t) { t.style.viewTransitionName = ""; });
    });
  }

  // A chart
  var chart = document.querySelector(".chart");
  var tools = document.querySelector("[data-tools]");
  if (chart && tools) {
    tools.hidden = false;
    var SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
    var FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"];
    var MAJOR = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"];
    var MINOR = ["Cm", "C#m", "Dm", "Ebm", "Em", "Fm", "F#m", "Gm", "G#m", "Am", "Bbm", "Bm"];
    var original = chart.getAttribute("data-key");
    var outs = document.querySelectorAll("[data-key-out]");
    var chords = Array.prototype.slice.call(chart.querySelectorAll(".c[data-c]"));
    var shift = 0;

    function idx(note) {
      var i = SHARP.indexOf(note);
      return i === -1 ? FLAT.indexOf(note) : i;
    }
    function parseKey(k) {
      var m = /^([A-G][#b]?)(m?)/.exec(k || "");
      return m ? { root: idx(m[1]), minor: m[2] === "m" } : null;
    }
    var base = parseKey(original);

    function keyName(n) {
      if (!base) return original;
      var i = (base.root + n + 120) % 12;
      return base.minor ? MINOR[i] : MAJOR[i];
    }
    function useFlats(name) {
      return /b/.test(name) || ["F", "Dm", "Gm", "Cm", "Fm"].indexOf(name) !== -1;
    }
    function move(note, n, flats) {
      var i = idx(note);
      return i === -1 ? note : (flats ? FLAT : SHARP)[(i + n + 120) % 12];
    }
    function transpose(chord, n, flats) {
      var m = /^([A-G][#b]?)([^/]*)(?:\/([A-G][#b]?))?$/.exec(chord);
      if (!m) return chord;
      return move(m[1], n, flats) + m[2] + (m[3] ? "/" + move(m[3], n, flats) : "");
    }

    function render() {
      var name = keyName(shift);
      var flats = useFlats(name);
      chords.forEach(function (el) {
        el.textContent = shift ? transpose(el.getAttribute("data-c"), shift, flats) : el.getAttribute("data-c");
      });
      each(outs, function (o) { o.textContent = name; });
      var params = new URLSearchParams(location.search);
      if (shift) params.set("key", name); else params.delete("key");
      var qs = params.toString();
      history.replaceState(null, "", qs ? "?" + qs : location.pathname);
    }

    var wanted = new URLSearchParams(location.search).get("key");
    if (wanted && base) {
      var w = parseKey(wanted);
      if (w) { shift = (w.root - base.root + 12) % 12; if (shift > 6) shift -= 12; render(); }
    }

    each(tools.querySelectorAll("[data-tr]"), function (b) {
      b.addEventListener("click", function () {
        var n = parseInt(b.getAttribute("data-tr"), 10);
        shift = n === 0 ? 0 : ((shift + n + 18) % 12) - 6;
        render();
      });
    });

    var toggle = tools.querySelector("[data-toggle-chords]");
    function setChords(on) {
      document.body.classList.toggle("no-chords", !on);
      toggle.setAttribute("aria-pressed", on ? "true" : "false");
    }
    setChords(store.get("chords") !== "off");
    toggle.addEventListener("click", function () {
      var on = toggle.getAttribute("aria-pressed") !== "true";
      setChords(on);
      store.set("chords", on ? "on" : "off");
    });

    var SIZES = [17, 19, 22, 26];
    var size = SIZES.indexOf(parseInt(store.get("size") || (innerWidth < 640 ? "17" : "19"), 10));
    if (size === -1) size = 1;
    function setSize(i) {
      size = i % SIZES.length;
      document.documentElement.style.setProperty("--chart-fs", SIZES[size] + "px");
      store.set("size", String(SIZES[size]));
    }
    setSize(size);
    tools.querySelector("[data-size]").addEventListener("click", function () { setSize(size + 1); });
    tools.querySelector("[data-print]").addEventListener("click", function () { window.print(); });
  }
})();
