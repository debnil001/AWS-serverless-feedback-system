const form = document.getElementById("feedbackForm");
const submitButton = document.getElementById("submitButton");
const status = document.getElementById("status");


const API_URL =
    "https://uwfpnglxse.execute-api.us-east-1.amazonaws.com/dev/feedback";


form.addEventListener("submit", async function (event) {

    event.preventDefault();

    submitButton.disabled = true;
    submitButton.textContent = "Submitting...";
    status.textContent = "";

    const name =
        document.getElementById("name").value.trim();

    const email =
        document.getElementById("email").value.trim();

    const message =
        document.getElementById("message").value.trim();

    const file =
        document.getElementById("file").files[0];


    try {

        let fileContent = null;
        let fileName = null;

        /*
         * If a PDF is selected,
         * convert it to Base64.
         */
        if (file) {

            if (file.type !== "application/pdf") {

                throw new Error(
                    "Only PDF files are allowed."
                );
            }

            if (file.size > 5 * 1024 * 1024) {

                throw new Error(
                    "PDF size must be less than 5 MB."
                );
            }

            fileName = file.name;

            fileContent = await fileToBase64(file);
        }


        /*
         * Send request to API Gateway
         */
        const response = await fetch(API_URL, {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({

                name: name,

                email: email,

                message: message,

                fileName: fileName,

                fileContent: fileContent

            })

        });


        const result = await response.json();


        if (!response.ok) {

            throw new Error(
                result.message || "Submission failed."
            );
        }


        /*
         * Successful submission
         */
        status.textContent =
            `Feedback submitted successfully! ID: ${result.feedbackId}`;

        form.reset();


    } catch (error) {

        console.error(
            "Submission error:",
            error
        );

        status.textContent =
            error.message ||
            "Something went wrong. Please try again.";

    } finally {

        submitButton.disabled = false;

        submitButton.textContent =
            "Submit Feedback";
    }

});


/*
 * Convert selected PDF to Base64
 */
function fileToBase64(file) {

    return new Promise((resolve, reject) => {

        const reader = new FileReader();

        reader.onload = () => {

            /*
             * FileReader returns:
             *
             * data:application/pdf;base64,XXXXX
             *
             * Lambda only needs XXXXX
             */

            const base64String =
                reader.result.split(",")[1];

            resolve(base64String);
        };

        reader.onerror = () => {

            reject(
                new Error(
                    "Unable to read the PDF file."
                )
            );
        };

        reader.readAsDataURL(file);
    });
}