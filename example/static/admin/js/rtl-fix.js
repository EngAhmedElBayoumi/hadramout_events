document.addEventListener("DOMContentLoaded", function () {
    const isRTL = document.documentElement.dir === "rtl";
    if (!isRTL) return;
    document.addEventListener("click", function () {
        document.querySelectorAll('[class*="-right-2"]').forEach(el => {
            el.classList.remove("-right-2");
            el.classList.add("-left-2");

        });
    });
    // change text-left to text-right
    document.querySelectorAll('[class*="text-left"]').forEach(el => {
        el.classList.remove("text-left");
        el.classList.add("text-right");
    });
});
