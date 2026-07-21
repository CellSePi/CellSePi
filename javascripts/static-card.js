document$.subscribe(() => {
  document.querySelectorAll(".custom-card.static-card").forEach((card) => {
    if (card.dataset.sweepBound) return;
    card.dataset.sweepBound = "true";

    card.addEventListener("mouseenter", () => {
      if (card.querySelectorAll(".sweep-streak").length >= 3) return;

      const sweep = document.createElement("span");
      sweep.className = "sweep-streak";
      sweep.addEventListener("animationend", () => sweep.remove());
      card.appendChild(sweep);
    });
  });
});