document.addEventListener("DOMContentLoaded", function () {

    // Lottie animation
    lottie.loadAnimation({
        container: document.getElementById("lottie-login"),
        renderer: "svg",
        loop: true,
        autoplay: true,
        path: "https://assets9.lottiefiles.com/packages/lf20_jcikwtux.json"
    });

});

// Password toggle
function togglePassword() {
    const pwd = document.getElementById("password");
    pwd.type = pwd.type === "password" ? "text" : "password";
}
