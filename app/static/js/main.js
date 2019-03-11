$(document).ready(function() {
   var visible_select_box_id = '#lang_pair'

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
    $("#output_text").val(translation);
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
      url: $(visible_select_box_id + " option:selected").val(),
      data: {'input_text': $("#input_text").val(),
             'src': $("#source option:selected").val(),
             'tgt': $("#target option:selected").val()
      },
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

  // checkbox actions
  $("#advanced").change(function(){
      $("#models").parents("div.form-group").toggleClass('hidden')
      $("#lang_pair").parents("div.form-group").toggleClass('hidden')
      visible_select_box_id = '#' + $("div.form-group:not(.hidden) > select").attr('id')

      // src tgt with model
      $("#source").parents("div.form-group").toggleClass('hidden')
      $("#target").parents("div.form-group").toggleClass('hidden')
  })

  // src tgt with model
    var select_source = $("#source")
    var select_target = $("#target")
    var get_model_options = function(model_url){
      return $.ajax({
          url: model_url,
          dataType: "json",
          success: function(data, status, request){
              select_source.off('change.languages')
              select_source.find("option").remove()
              select_target.find("option").remove()
              var create_option = function(value){
                 var option = $("<option/>")
                 option.attr('value', value)
                 option.text(value)
                 return option
              }
              Object.keys(data.supports).forEach(function(key){
                  var option = create_option(key)
                  select_source.append(option)
              })
              select_source.on('change.languages', function(e){
                  var key = $(e.target).val()
                  var supported_tgt_arr = data.supports[key]
                  select_target.find("option").remove()
                  supported_tgt_arr.forEach(function(tgt_lang){
                      var option = create_option(tgt_lang)
                      select_target.append(option)
                  })
              })
              //add_options(select_target, data.target)
              //console.log(data)
          },
          error: function (jqXHR, textStatus, errorThrown) {
              console.error(textStatus)
          }
      })
    }
    $("#models").change(function(e){
        var model_url = $(e.target).val()
        get_model_options(model_url).done(function(){
            select_source.trigger('change')
        })
    })
    $("#models").trigger('change')

  // fileupload
  if (!!FileReader && 'draggable' in document.createElement('span')
			&& !!window.FormData && "upload" in new XMLHttpRequest && !!window.Blob && !!window.FileReader) {
            var $file_field = $("input[type='file']")
				$file_field.change(function() {
                    var files = document.getElementById("data_file").files;
                    if(files.length > 0) {
                        if (files[0].size > $FILE_SIZE_LIMIT) {
                            alert('The file is too large.\nThe maximal allowed content length is ' + $FILE_SIZE_LIMIT + 'B.')
                            event.preventDefault()
                            return
                        }
                        if (files[0].type !== 'text/plain'){
                            alert(files[0].type + ' not allowed. Only text/plain.')
                            event.preventDefault()
                            return
                        }
                        var reader = new FileReader();
                        reader.onload = function(event){
                            $("#input_text").val(event.target.result)
                            $("#input_text").trigger('paste')
                        }
                        //console.log(files[0])
                        reader.readAsText(files[0]);
                    }
				});
		}

  // textarea auto translate
    var countDownTimer;
    var cancelCountDown = function(){
        clearTimeout(countDownTimer)
    }
    var countDown = function(){
        cancelCountDown()
        countDownTimer = setTimeout(function(){
            //console.log("sending " + $("#input_text").val())
            if($("#input_text").val()){
                $("#submit").click()
            }
        }, 1500)
    }
    // TODO mobile seems lacking keyup/keydown
    $("#input_text").on("keyup", countDown)
                    .on("keydown", cancelCountDown)
                    .on("paste", countDown)
    $("#lang_pair").on("change", countDown)
    $("#models").on("change", countDown)
    $("#advanced").on("change", countDown)
    $("#source").on("change", countDown)
    $("#target").on("change", countDown)
});
