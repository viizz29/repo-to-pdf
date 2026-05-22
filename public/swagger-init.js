(function () {
  function attachSwaggerAuth() {
    const ui = window.ui;
    if (!ui || ui.__bearerPatchApplied) {
      return Boolean(ui);
    }

    ui.__bearerPatchApplied = true;

    const originalFetch = window.fetch.bind(window);
    window.fetch = async function (...args) {
      const response = await originalFetch(...args);
      const requestUrl = typeof args[0] === "string" ? args[0] : args[0]?.url;

      if (requestUrl && requestUrl.includes("/auth/login") && response.ok) {
        try {
          const responseClone = response.clone();
          const responseBody = await responseClone.json();
          const token = responseBody?.token;

          if (token) {
            ui.preauthorizeApiKey("bearerAuth", token);
          }
        } catch (error) {
          console.error("Failed to preauthorize bearer token", error);
        }
      }

      return response;
    };

    return true;
  }

  if (!attachSwaggerAuth()) {
    const intervalId = window.setInterval(function () {
      if (attachSwaggerAuth()) {
        window.clearInterval(intervalId);
      }
    }, 250);
  }
})();
