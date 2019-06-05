Using Module ./venariapi.psm1

<#
Oath credentials file format:
{
    "tokenEndpoint":"",
    "clientId":"",
    "clientSecret":"",
    "scope":"",
    "username":""
}
Json files should be in ~/assert-security/testdata. The name of the file without
the extension is the credential name.
#>

$credentials=@()
gci ~/assert-security/testdata/*.json | %{
    $credentials+=@{  
        App=$_.Name.replace(".json","")
        Config=$_.FullName
    }
}


function Get-CredentialsByName{
    param(
        $name
    )
    $found=  gc ($credentials | Where {$_.App -eq $name}).Config  | convertfrom-json
    return $found
    

}

function Test-AppCredentials(){
    $credentials | %{
        
        $cfg=(gc $_.Config | convertfrom-json )
        $cfg |fl
        $endpoint=New-Object AuthEndpointInfo -ArgumentList $cfg.tokenEndpoint,$cfg.scope,$cfg.clientId
        $auth=New-Object Auth -ArgumentList $endpoint
        $secret=ConvertTo-SecureString -AsPlainText -Force "$($cfg.clientSecret)"
        $auth.Login($secret)
        write-host "$($_.Name) Results:"
        $auth.decodedaccesstoken.payload | fl
    }
}

function Test-GetJob{
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true,ValueFromPipeline = $true)]        
        $configName,
        $apiUrl
    )
    $cfg=Get-CredentialsByName $configName
    $endpoint=New-Object AuthEndpointInfo -ArgumentList $cfg.tokenEndpoint,$cfg.scope,$cfg.clientId
    $auth=New-Object Auth -ArgumentList $endpoint

    $secret=ConvertTo-SecureString -AsPlainText -Force "$($cfg.clientSecret)"
    $auth.Login($secret)
    $auth.decodedaccesstoken.payload | fl
    $api=New-Object VenariAutomation -ArgumentList $auth,$apiUrl
    
    $jobs=$api.GetJob()
    $jobs | fl
}

function Test-GetWorkspaces{
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true,ValueFromPipeline = $true)]        
        $configName,
        $apiUrl
    )

    $auth=Get-Auth -configName $configName -apiUrl $apiUrl
    $api=New-Object VenariAutomation -ArgumentList $auth,$apiUrl
    
    $workspaces=$api.GetWorkspaces($null)
    $workspaces | fl    
}


function Test-GetWorkspaceByName{
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true,ValueFromPipeline = $true)]        
        $configName,
        $apiUrl,
        $WorkspaceName
    )

    $auth=Get-Auth -configName $configName -apiUrl $apiUrl
    $api=New-Object VenariAutomation -ArgumentList $auth,$apiUrl
    $workspaces=$api.GetWorkspaces($WorkspaceName)
    $workspaces | fl    
}

function Test-GetFindings{
    param(
        [Parameter(Mandatory = $true,ValueFromPipeline = $true)]        
        $configName,
        $apiUrl,
        $WorkspaceName
    )
    $auth=Get-Auth -configName $configName -apiUrl $apiUrl
    $api=New-Object VenariAutomation -ArgumentList $auth,$apiUrl
    $workspace=$api.GetWorkspaces($WorkspaceName)
    $workspace.SummaryData | fl    

    $findings=$api.GetFindings($workspace)
    $findings | fl
}

function Get-Auth{
    param(
        [Parameter(Mandatory = $true,ValueFromPipeline = $true)]        
        $configName,
        $apiUrl
    )
    $cfg=Get-CredentialsByName $configName
    $endpoint=New-Object AuthEndpointInfo -ArgumentList $cfg.tokenEndpoint,$cfg.scope,$cfg.clientId
    $auth=New-Object Auth -ArgumentList $endpoint

    $secret=ConvertTo-SecureString -AsPlainText -Force "$($cfg.clientSecret)"
    $auth.Login($secret)
    $auth
}