
pipeline{
    parameters{
        choice(
            choices: ['JOBTEMPLATES', 'URLS'], 
            name: 'START_METHOD',
            description:'Optionally deploy the UI to the hotfix or updates location'
        )
    }
    agent any
    environment {
        DEVOPS_API_KEY = credentials('devops-api-key')
    }
    stages{
        stage('Run Job Templates'){
            when {
                expression {
                    return params.START_METHOD=='JOBTEMPLATES'
                }
            }
            steps{
                script{
                    pwsh '''
                        \$ErrorActionPreference = "Stop"
                        ./run-job-templates.ps1
                    '''
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
                script{
                    pwsh '''
                        \$ErrorActionPreference = "Stop"
                        ./run-urls.ps1
                    '''
                }
            }
        }
    }
}