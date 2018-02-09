$(document).ready(function() {

  // flash an alert
  // remove previous alerts by default
  // set clean to false to keep old alerts
  function flash_alert(message, category, clean) {
    console.log(message);
    if (typeof(clean) === "undefined") clean = true;
    if(clean) {
      remove_alerts();
    }
    var htmlString = '<div class="alert alert-' + category + ' alert-dismissible" role="alert">'
    htmlString += '<button type="button" class="close" data-dismiss="alert" aria-label="Close">'
    htmlString += '<span aria-hidden="true">&times;</span></button>' + message + '</div>'
    $(htmlString).prependTo("#mainContent").slideDown();
  }

  function remove_alerts() {
    $(".alert").slideUp("normal", function() {
      $(this).remove();
    });
  }

  function show_translation(translation) {
    var htmlString = '<pre>';
    var $pre = $(htmlString);
    $pre.text(translation);
    $pre.appendTo("#mainContent");
  }

  function check_job_status(status_url) {
  $.getJSON(status_url, function(data) {
    console.log(data);
    switch (data.status) {
      case "unknown":
          flash_alert("Unknown job id", "danger");
          $("#submit").removeAttr("disabled");
          break;
      case "finished":
          flash_alert("Success", "success");
          show_translation(data.result)
          $("#submit").removeAttr("disabled");
          break;
      case "failed":
          flash_alert("Job failed: " + data.message, "danger");
          $("#submit").removeAttr("disabled");
          break;
      default:
        // queued/started/deferred
        setTimeout(function() {
          check_job_status(status_url);
        }, 500);
    }
  });
}

  // submit form
  $("#submit").on('click', function() {
    flash_alert("Running  ...", "info");
    $.ajax({
      url: $SCRIPT_ROOT + "/_run_task",
      data: $("#taskForm").serialize(),
      method: "POST",
      dataType: "json",
      success: function(data, status, request) {
        $("#submit").attr("disabled", "disabled");
        flash_alert("Running ...", "info");
        var status_url = request.getResponseHeader('Location');
        check_job_status(status_url)
      },
      error: function(jqXHR, textStatus, errorThrown) {
          flash_alert("Failed to start", "danger");
      }
    });
  });

});