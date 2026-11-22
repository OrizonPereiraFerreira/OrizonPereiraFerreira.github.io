// Renders the page from js/data.js. To add a paper, a repository or a student, edit data.js only.
(function () {
  "use strict";
  const ME = /O\.\s*P\.\s*Ferreira/;
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const el = (id) => document.getElementById(id);

  function authors(list) {
    const P = DATA.people || {};
    return list
      .map((a) => {
        if (ME.test(a)) return "<b>" + esc(a) + "</b>";
        return P[a] ? "<a class='coauthor' href='" + esc(P[a]) + "'>" + esc(a) + "</a>" : esc(a);
      })
      .join(", ");
  }

  function badges(p) {
    const b = [];
    if (p.url) b.push('<a class="badge" href="' + esc(p.url) + '">' + (p.url.includes("doi.org") ? "DOI" : "Link") + "</a>");
    if (p.pdf) b.push('<a class="badge" href="' + esc(p.pdf) + '">PDF</a>');
    if (p.code) b.push('<a class="badge code" href="' + esc(p.code) + '">Code</a>');
    return b.length ? '<span class="badges">' + b.join("") + "</span>" : "";
  }

  function pubItem(p, n) {
    const title = p.url ? '<a href="' + esc(p.url) + '">' + p.title + "</a>" : p.title;
    const ref = [p.ref, p.year].filter(Boolean).join(", ");
    return (
      "<li><span class='num'>" + (n || "") + "</span><div>" +
      "<div class='authors'>" + authors(p.authors) + "</div>" +
      "<div class='ptitle'>" + title + (p.status ? "<span class='status'>" + esc(p.status) + "</span>" : "") + "</div>" +
      "<div class='venue'><i>" + esc(p.venue || "") + "</i>" + (ref ? ", " + esc(ref) : "") + "." + badges(p) + "</div>" +
      "</div></li>"
    );
  }

  // Publications
  const groups = DATA.publications; // [{name, items:[...]}]
  const total = groups.reduce((s, g) => s + g.items.length, 0);
  el("pub-count").textContent = total + " items";

  function renderPubs() {
    const q = el("pub-search").value.trim().toLowerCase();
    const onlyCode = el("pub-code").checked;
    let shown = 0;
    const html = groups
      .map((g) => {
        const items = g.items.filter((p) => {
          if (onlyCode && !p.code) return false;
          if (!q) return true;
          const hay = (p.authors.join(" ") + " " + p.title + " " + (p.venue || "") + " " + (p.year || "")).toLowerCase();
          return q.split(/\s+/).every((w) => hay.includes(w));
        });
        if (!items.length) return "";
        shown += items.length;
        let out = "<h3>" + esc(g.name) + "</h3>";
        if (g.byYear) {
          let year = null, buf = "";
          items.forEach((p) => {
            if (p.year !== year) {
              if (buf) out += "<ol class='pubs'>" + buf + "</ol>";
              buf = "";
              year = p.year;
              out += "<div class='year'>" + esc(year) + "</div>";
            }
            buf += pubItem(p, p.n);
          });
          if (buf) out += "<ol class='pubs'>" + buf + "</ol>";
        } else {
          out += "<ol class='pubs'>" + items.map((p) => pubItem(p, p.n)).join("") + "</ol>";
        }
        return out;
      })
      .join("");
    el("pub-list").innerHTML = html || "<p class='note'>No publication matches the search.</p>";
    el("pub-shown").textContent = shown === total ? "" : shown + " shown";
  }
  el("pub-search").addEventListener("input", renderPubs);
  el("pub-code").addEventListener("change", renderPubs);
  renderPubs();

  // Supervision
  function people(list) {
    return (
      "<ol class='people'>" +
      list
        .map(
          (s) =>
            "<li><span class='y'>" + esc(s.year) + "</span><div><div class='who'>" +
            (s.lattes ? "<a href='" + esc(s.lattes) + "'>" + esc(s.name) + "</a>" : esc(s.name)) + "</div>" +
            "<div class='what'>" + (s.doc ? "<a href='" + esc(s.doc) + "'>" + esc(s.title) + "</a>" : esc(s.title)) + "</div>" +
            "<div class='inst'>" + esc(s.info) + "</div></div></li>"
        )
        .join("") +
      "</ol>"
    );
  }
  el("students").innerHTML =
    "<h3>Current students</h3>" + people(DATA.students.current) +
    "<h3>Ph.D. theses (" + DATA.students.phd.length + ")</h3>" + people(DATA.students.phd) +
    "<h3>Master's dissertations (" + DATA.students.msc.length + ")</h3>" + people(DATA.students.msc);

  // Events
  const ev = (e) =>
    "<li><a href='" + esc(e.url) + "'>" + esc(e.name) + "</a><span class='detail'>" + esc(e.detail) + "</span></li>";
  const E = DATA.events;
  const nPrev = E.previous.reduce((s, y) => s + y.items.length, 0);
  el("events-list").innerHTML =
    "<h3>Forthcoming</h3><ul class='events'>" + E.forthcoming.map(ev).join("") + "</ul>" +
    "<details class='past'><summary>Previous events (" + nPrev + ")</summary>" +
    E.previous.map((y) => "<div class='year'>" + y.year + "</div><ul class='events'>" + y.items.map(ev).join("") + "</ul>").join("") +
    "<div class='year'>Seminar series</div><ul class='events'>" + E.series.map(ev).join("") + "</ul>" +
    "</details>";

  el("updated").textContent = DATA.updated;

  // Links to other sites open in a new tab; links to sections of this page do not.
  document.querySelectorAll('a[href^="http"], a[href^="//"]').forEach((a) => {
    a.target = "_blank";
    a.rel = "noopener noreferrer";
  });

  // The menu works as tabs: only the selected section is shown, and the bar stays on screen.
  const sections = Array.from(document.querySelectorAll("main > section"));
  const navLinks = Array.from(document.querySelectorAll(".navbar nav a"));
  function show(id) {
    if (!sections.some((s) => s.id === id)) id = sections[0].id;
    sections.forEach((s) => { s.hidden = s.id !== id; });
    navLinks.forEach((a) => {
      const on = a.getAttribute("href") === "#" + id;
      a.classList.toggle("active", on);
      if (on) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
    });
    window.scrollTo(0, 0);
  }
  window.addEventListener("hashchange", () => show(location.hash.slice(1)));
  show(location.hash.slice(1));
})();
