
const styleLink = document.getElementById("style");

const browserPrefersDarkTheme = () => {
    /*if (!userIsAuthenticated){
        return false;  // For non-authenticated users, always use default "light" theme
    }*/
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
}

const switchToDarkMode = () => {
    styleLink.setAttribute('href', '/static/bw-frontend/dist/index-dark.css');
}

const switchToLightMode = () => {
    styleLink.setAttribute('href', '/static/bw-frontend/dist/index.css');
}

const isUsingDarkTheme = () => {
    return styleLink.getAttribute('href').indexOf('dark') > -1;
}

window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', event => {
    const newColorScheme = event.matches ? "dark" : "light";
    if (styleLink.dataset.forcedTheme === undefined){
        if (newColorScheme == "dark"){
            switchToDarkMode();
        } else if (newColorScheme == "dark"){
            switchToLightMode();
        }
    }
});


if (browserPrefersDarkTheme()){
    document.cookie = "systemPrefersDarkTheme=yes;path=/";
} else {
    document.cookie = "systemPrefersDarkTheme=no;path=/";
}

if (styleLink.dataset.forcedTheme === undefined){
    if (browserPrefersDarkTheme() && !isUsingDarkTheme()){
        switchToDarkMode();
    } else if (!browserPrefersDarkTheme() && isUsingDarkTheme()){
        switchToLightMode();
    }
}

