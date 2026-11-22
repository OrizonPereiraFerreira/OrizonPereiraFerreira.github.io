// Renders the page from js/data.js. To add a paper, a repository or a student, edit data.js only.
(function () {
  "use strict";
  const ME = /O\.\s*P\.\s*Ferreira/;
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const el = (id) => document.getElementById(id);

  function authors(list) {
    return list.map((a) => (ME.test(a) ? "<b>" + esc(a) + "</b>" : esc(a))).join(", ");
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

  // Code
  el("code-cards").innerHTML = DATA.code
    .map(
      (r) =>
        "<div class='card'><div class='repo'>" + esc(r.repo) + "</div>" +
        "<div class='ptitle'>" + r.title + "</div>" +
        "<div class='meta'>" + esc(r.authors) + ". " + esc(r.venue) + "</div>" +
        "<div class='row'><span class='chip'>" + esc(r.language) + "</span>" +
        "<a href='" + esc(r.url) + "'>Repository →</a></div></div>"
    )
    .join("");
  el("code-count").textContent = DATA.code.length + " repositories";
  el("code-note").innerHTML = DATA.codeNote || "";

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

  el("updated").textContent = DATA.updated;

  // Links to other sites open in a new tab; links to sections of this page do not.
  document.querySelectorAll('a[href^="http"], a[href^="//"]').forEach((a) => {
    a.target = "_blank";
    a.rel = "noopener noreferrer";
  });

  // The lists are built by this script, so jump to the requested section once they exist.
  if (location.hash) {
    const target = document.getElementById(location.hash.slice(1));
    if (target) target.scrollIntoView();
  }
})();
