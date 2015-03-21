function sendconfirm(rcode){
    $.post("/confirm",
    {
        "rcode":rcode,
    },
    function(data){
        alert(data);
        $("#a").remove();
    });
};