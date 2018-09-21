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
    $(htmlString).prependTo(".panel-group").hide().slideDown();
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
    $pre.appendTo("#tab1");
  }

  // submit form
  $("#submit").on('click', function() {
    flash_alert("Running  ...", "info");
    var counter = 0;
    var progress = setInterval(function() {
          var dots = Array((++counter % 5) + 2).join(".");
          var message = "Running" + dots;
          flash_alert(message, "info");
      }, 1500);
    $("#submit").attr("disabled", "disabled");
    $.ajax({
      url: $SCRIPT_ROOT + "/translate",
      data: $("#taskForm").serialize(),
      method: "POST",
      dataType: "json",
      success: function(data, status, request) {
          clearInterval(progress);
          flash_alert("Success", "success");
          show_translation(data.join('\n'));
          $("#submit").removeAttr("disabled");
      },
      error: function(jqXHR, textStatus, errorThrown) {
          clearInterval(progress);
          flash_alert("Translation failed: " + textStatus + "\n" + errorThrown, "danger");
      }
    });
  });

});
