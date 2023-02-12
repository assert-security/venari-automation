
pipeline{
    parameters{
        choice(
            choices: ['JOBTEMPLATES', 'URLS'], 
            name: 'START_METHOD',
            description:'Optionally deploy the UI to the hotfix or updates location'
        )
    }
    agent { label 'master' }
    stages{
        stage('Run Job Templates'){
            when {
                expression {
                    return params.START_METHOD=='JOBTEMPLATES-CURRENT'
                }
            }
            steps{
                script{
                    withCredentials([usernamePassword(credentialsId: 'devops-api-key', passwordVariable: 'DEVOPS_API_KEY')]) {
                        pwsh '''
                            \$ErrorActionPreference = "Stop"
                            ./run-job-templates.ps1 -apiKey $DEVOPS_API_KEY
                        '''
                    }
                }
            }
        }
        stage('Run URLs'){
            when {
                expression {
                    return params.START_METHOD=='URLS'
                }
            }
            steps{
                withCredentials([usernamePassword(credentialsId: 'devops-api-key', passwordVariable: 'DEVOPS_API_KEY')]) {
                    script{
                        pwsh '''
                            \$ErrorActionPreference = "Stop"
                            ./run-urls.ps1 -apiKey $DEVOPS_API_KEY
                        '''
                    }
                }
            }
        }
    }
}