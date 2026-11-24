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

  const ICON = {
    link: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 14a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1"/><path d="M14 10a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"/></svg>',
    pdf: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/></svg>',
    code: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m8 7-5 5 5 5"/><path d="m16 7 5 5-5 5"/></svg>'
  };

  function badges(p) {
    const b = [];
    if (p.url) b.push('<a class="badge" href="' + esc(p.url) + '">' + ICON.link + (p.url.includes("doi.org") ? "DOI" : p.url.includes("arxiv.org") ? "arXiv" : "Link") + "</a>");
    if (p.pdf) b.push('<a class="badge" href="' + esc(p.pdf) + '">' + ICON.pdf + "PDF</a>");
    if (p.code) b.push('<a class="badge code" href="' + esc(p.code) + '">' + ICON.code + "Code</a>");
    return b.length ? '<span class="badges">' + b.join("") + "</span>" : "";
  }

  function pubItem(p) {
    const title = p.url ? '<a href="' + esc(p.url) + '">' + p.title + "</a>" : p.title;
    const venue = p.venueUrl ? "<a class='journal' href='" + esc(p.venueUrl) + "'>" + esc(p.venue) + "</a>" : esc(p.venue || "");
    const ref = [p.ref, p.year].filter(Boolean).join(", ");
    return (
      "<li class='pub" + (p.n ? "" : " nonum") + "'>" +
      "<span class='num'>" + (p.n ? p.n : "") + "</span>" +
      "<div class='body'>" +
      "<div class='ptitle'>" + title + (p.status ? " <span class='status'>" + esc(p.status) + "</span>" : "") + "</div>" +
      "<div class='authors'>" + authors(p.authors) + "</div>" +
      "<div class='venue'><i>" + venue + "</i>" + (ref ? ", " + esc(ref) : "") + badges(p) + "</div>" +
      "</div></li>"
    );
  }

  // Publications
  const groups = DATA.publications; // [{name, byYear, items:[...]}]
  const total = groups.reduce((s, g) => s + g.items.length, 0);
  const SHORT = { "Articles in journals": "Journals", "Expository articles": "Expository", "Book chapter": "Book chapter", "Ph.D. thesis": "Thesis" };
  let cat = "all";
  el("pub-count").textContent = total + " items";
  el("pub-cats").innerHTML =
    "<button type='button' data-cat='all' class='on'>All <span>" + total + "</span></button>" +
    groups.map((g, i) => "<button type='button' data-cat='" + i + "'>" + esc(SHORT[g.name] || g.name) + " <span>" + g.items.length + "</span></button>").join("");
  el("pub-cats").addEventListener("click", (e) => {
    const btn = e.target.closest("button");
    if (!btn) return;
    cat = btn.dataset.cat;
    el("pub-cats").querySelectorAll("button").forEach((b) => {
      b.classList.toggle("on", b === btn);
      b.setAttribute("aria-pressed", b === btn ? "true" : "false");
    });
    renderPubs();
  });

  function renderPubs() {
    const q = el("pub-search").value.trim().toLowerCase();
    const onlyCode = el("pub-code").checked;
    let shown = 0;
    const html = groups
      .map((g, gi) => {
        if (cat !== "all" && String(gi) !== cat) return "";
        const items = g.items.filter((p) => {
          if (onlyCode && !p.code) return false;
          if (!q) return true;
          const hay = (p.authors.join(" ") + " " + p.title.replace(/<[^>]+>/g, "") + " " + (p.venue || "") + " " + (p.year || "")).toLowerCase();
          return q.split(/\s+/).every((w) => hay.includes(w));
        });
        if (!items.length) return "";
        shown += items.length;
        let out = "<div class='pubgroup'><h3>" + esc(g.name) + " <span class='gcount'>" + items.length + "</span></h3>";
        if (g.byYear) {
          const years = [];
          items.forEach((p) => {
            const last = years[years.length - 1];
            if (last && last.year === p.year) last.items.push(p);
            else years.push({ year: p.year, items: [p] });
          });
          out += years
            .map((y) => "<div class='ygroup'><div class='ylabel'><span>" + esc(y.year) + "</span></div><ol class='pubs'>" + y.items.map(pubItem).join("") + "</ol></div>")
            .join("");
        } else {
          out += "<ol class='pubs'>" + items.map(pubItem).join("") + "</ol>";
        }
        return out + "</div>";
      })
      .join("");
    el("pub-list").innerHTML = html || "<p class='empty'>No publication matches the search.</p>";
    el("pub-shown").textContent = shown === total ? "" : shown + " of " + total + " shown";
    el("pub-list").querySelectorAll('a[href^="http"]').forEach((a) => { a.target = "_blank"; a.rel = "noopener noreferrer"; });
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

  // The header is fixed; the page starts below it, whatever its height on this screen.
  const head = document.querySelector(".masthead");
  const side = document.querySelector(".aside-inner");
  const layout = document.querySelector(".layout");
  const setHead = () => {
    document.documentElement.style.setProperty("--head", head.offsetHeight + "px");
    // the pinned side column takes no room in the page, so keep the page at least as tall as it
    layout.style.minHeight = getComputedStyle(side).position === "fixed" ? side.scrollHeight + 72 + "px" : "";
  };
  setHead();
  window.addEventListener("resize", setHead);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(setHead);

  // The menu works as tabs: only the selected section is shown, and the bar stays on screen.
  const sections = Array.from(document.querySelectorAll("main > section"));
  const navLinks = Array.from(document.querySelectorAll(".masthead nav a"));
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
