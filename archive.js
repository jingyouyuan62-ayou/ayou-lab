const grid = document.getElementById("archive-grid");
const status = document.getElementById("archive-status");
const filterButtons = document.querySelectorAll(".filter-btn");

fetch("data/entries.json", { cache: "no-store" })
    .then((response) => {
        if (!response.ok) {
            throw new Error("Failed to load entries.json");
        }
        return response.json();
    })
    .then((entries) => {
        status.remove();

        if (entries.length === 0) {
            grid.textContent = "The archive is still growing.";
            return;
        }

        entries.forEach((entry) => {
            grid.appendChild(createCard(entry));
        });
    })
    .catch((error) => {
        status.textContent = "Could not load the archive. " + error.message;
    });

filterButtons.forEach((button) => {
    button.addEventListener("click", () => {
        filterButtons.forEach((b) => b.classList.remove("active"));
        button.classList.add("active");
        applyFilter(button.dataset.filter);
    });
});

function applyFilter(filter) {
    const cards = grid.querySelectorAll(".entry-card");
    cards.forEach((card) => {
        const show = filter === "all" || card.dataset.category === filter;
        card.classList.toggle("is-hidden", !show);
    });
}

function createCard(entry) {
    const card = document.createElement("article");
    card.className = "entry-card";
    card.dataset.category = entry.category;
    card.style.setProperty("--accent", entry.accent || "#b8543d");

    const media = document.createElement("div");
    media.className = "entry-card-media";

    const image = document.createElement("img");
    image.src = entry.image;
    image.alt = entry.title;
    image.loading = "lazy";

    media.appendChild(image);

    const body = document.createElement("div");
    body.className = "entry-card-body";

    const title = document.createElement("h2");
    title.textContent = entry.title;

    const meta = document.createElement("p");
    meta.className = "entry-meta";
    meta.textContent = `${entry.date} · ${entry.medium} · ${entry.source}`;

    const note = document.createElement("p");
    note.className = "entry-note";
    note.textContent = entry.note;

    body.append(title, meta, note);

    const confirmed =
        entry.echoes && Array.isArray(entry.echoes.confirmed)
            ? entry.echoes.confirmed
            : [];

    if (confirmed.length > 0) {
        const echo = document.createElement("p");
        echo.className = "entry-echo";
        echo.textContent = "↳ " + confirmed.join(" · ");
        body.append(echo);
    }

    const category = document.createElement("p");
    category.className = "entry-tags";
    category.textContent = entry.category.toUpperCase();

    body.append(category);
    card.append(media, body);

    return card;
}
