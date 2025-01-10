pipeline {
    agent any
    parameters{
        string(
            name: 'MASTER_ADDRESS', 
            trim: true
        )
    }

    stages {

        stage('Run Venari DevOps Scan') {
            steps {
                script {
                    
                    if (params.MASTER_ADDRESS != null 
                        && params.MASTER_ADDRESS.length() > 0) {
                        try {

                            def entry = input( id: 'venariDevOpsAPIKey', message: 'Enter Venari DevOps API Key', parameters: [password(defaultValue: 'value', description: '', name: 'hidden')])
                            def apiKey = entry.toString();
                            def response =  httpRequest acceptType: 'APPLICATION_JSON',
                                customHeaders: [[maskValue: true, name: 'X-API-KEY', value: apiKey]], 
                                url: "${params.MASTER_ADDRESS}/api/devops/applications"
                            
                            // Get response code
                            if (response.status != 200) {
                                throw new Exception(response.content)
                            } 
                            else {
                                def json = response.content;
                                def appList = readJSON text: json;
                                def applications = []
                                for (app in appList) {
                                    applications.add(app.DisplayName);
                                }
                                def application = input( id: 'userInput', message: 'Select Venari DevOps application', parameters: [ [$class: 'ChoiceParameterDefinition', choices: applications, description: '', name: ''] ])
                                println "Selected application: " + application

                                def jobTemplates = []
                                def appId
                                for (app in appList) {
                                    if (app.DisplayName == application) {
                                        appId = app.Id
                                    }
                                }
                                response =  httpRequest acceptType: 'APPLICATION_JSON',
                                    customHeaders: [[maskValue: true, name: 'X-API-KEY', value: apiKey]], 
                                    url: "${params.MASTER_ADDRESS}/api/devops/jobtemplates/${appId}/templates"
                                json = response.content;
                                def jobTemplateList = readJSON text: json
                                for (jt in jobTemplateList) {
                                    jobTemplates.add(jt.Name)
                                }
                                def jobTemplate = input( id: 'userInput', message: 'Select Venari DevOps configuration', parameters: [ [$class: 'ChoiceParameterDefinition', choices: jobTemplates, description: '', name: ''] ])
                                println "Selected configuration: " + jobTemplate

                                httpRequest acceptType: 'APPLICATION_JSON', contentType: 'APPLICATION_JSON',
                                            httpMode: 'POST', quiet: true,
                                            requestBody: """{
                                            "ApplicationName" : "${application}",
                                            "JobTemplateName" : "${jobTemplate}",
                                            }""",
                                            customHeaders: [[maskValue: true, name: 'X-API-KEY', value: apiKey]],
                                            url: "${params.MASTER_ADDRESS}/api/devops/jobs/create"
                            }

                        } 
                        catch (Exception e) {
                            // Handle the exception
                            println "Caught an exception: ${e.message}"
                            throw e;
                        }
                    }
                    else {
                        throw new Exception("Missing parameters: MASTER_ADDRESS or API_KEY")
                    }
                }
            }
        }
    }
}
