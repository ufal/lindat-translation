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
    $pre.appendTo("#tab");
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
      url: $("#lang_pair option:selected").val(),
      data: {'input_text': $("#input_text").val()},
      method: "POST",
      dataType: "json",
      success: function(data, status, request) {
          clearInterval(progress);
          flash_alert("Success", "success");
          show_translation(data.join(' ').replace(/\n /g, '\n'));
          $("#submit").removeAttr("disabled");
      },
      error: function(jqXHR, textStatus, errorThrown) {
          clearInterval(progress);
          flash_alert("Translation failed: " + textStatus + "\n" + errorThrown, "danger");
      }
    });
  });

  // fileUpload button
  $("#translate").on('click', function (e){
      var data_file = $('#data_file')
      if(data_file.size() > 0 && data_file[0].files.length) {
          if (data_file[0].files[0].size > $FILE_SIZE_LIMIT) {
              alert('The file is too large.\nThe maximal allowed content length is ' + $FILE_SIZE_LIMIT + 'B.')
              e.preventDefault()
          }
          if (data_file[0].files[0].type !== 'text/plain'){
              alert(data_file[0].files[0].type + ' not allowed. Only text/plain.')
              e.preventDefault()
          }
      }
  })
});
