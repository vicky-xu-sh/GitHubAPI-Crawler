from github_api import GitHubAPI

if __name__ == "__main__":
    api = GitHubAPI()
    
    # get upstream repo name (change this)
    repo_name = "OpenVPN/openvpn"

    # get all the forks names & created time & last pushed time
    forksCreatedTime = {}
    forkNames = []
    forks_url = "repos/%s/forks" % repo_name
    for fork in api.request(forks_url, paginate=True):
        fork_name = fork['full_name']
        createdTime = fork['created_at']
        lastpushed = fork['pushed_at']
        forksCreatedTime[fork_name] = {"created_at": createdTime, "pushed_at": lastpushed}
        forkNames.append(fork_name)
    
    # create a directory to contain all cloned repositories
    if not os.path.isdir("./cloned"):
        os.mkdir("./cloned")
    if not os.path.isdir("./cloned/forks"):
        os.mkdir("./cloned/forks")
    
    # clone all forks
    count = 0
    for fork_name in forkNames:
        
        # check if the last pushed time is later than created time, only clone if so
        times_dict = forksCreatedTime[fork_name]
        fork_created_time = datetime.datetime.strptime(times_dict["created_at"], "%Y-%m-%dT%H:%M:%SZ")
        fork_pushed_time = datetime.datetime.strptime(times_dict["pushed_at"], "%Y-%m-%dT%H:%M:%SZ")

        #nothing pushed after fork has created means non-active fork, skip this one
        if fork_created_time > fork_pushed_time:
            continue

        forkPathName = fork_name.split('/')[0]

        #check if directory exists (already cloned)
        if os.path.isdir('./cloned/forks/%s' % forkPathName) == False:
            fork_repo_url = "git://github.com/%s.git" % fork_name
            fork_repo_path = './cloned/forks/%s' % forkPathName

            try:
                fork_repo = clone_repository(fork_repo_url, fork_repo_path) # Clones a non-bare repository
            except GitError as err:
                # if can't clone, throw an error
                print ("error: %s " % forkPathName)
        count += 1

    #total number of cloned forks
    #print(count)
    
    
    
    # create a directory to contain all cloned repo git logs
    upstream = repo_name.split('/')[0]
    if not os.path.isdir("./data/%s-git-log/" % upstream):
        os.mkdir("./data/%s-git-log/" % upstream)
    
    # get git log of cloned repo
    count = 0
    for fork_name in forkNames:
        forkPathName = fork_name.split('/')[0]

        #check if directory exists (already cloned)
        if os.path.isdir('./cloned/forks/%s' % forkPathName) == True:
            times_dict = forksCreatedTime[fork_name]
            forkingPoint = times_dict['created_at']
            output = subprocess.check_output("git log --raw --after=%s" % forkingPoint, stderr=subprocess.STDOUT, shell=True, cwd='./cloned/forks/%s' % forkPathName).decode()

            #if output empty, don't create a txt file
            if output:
                count += 1
                f = open("./data/%s-git-log/%s.txt" % (upstream, forkPathName),"w+")
                f.write(output)
                f.close
        else: 
            print ("not cloned: %s " % forkPathName)
    
    
    # create a directory to contain all parsed cloned repo git logs
    upstream = repo_name.split('/')[0]
    if not os.path.isdir("./data/%s-parsed/" % upstream):
        os.mkdir("./data/%s-parsed/" % upstream)

    # read and parse git log txt file
    for fork_name in forkNames:
        forkPathName = fork_name.split('/')[0]

        #if the txt file doesn't exist for the fork, skip
        if os.path.isfile('./data/%s-git-log/%s.txt' % (upstream, forkPathName)) == False:
            continue

        with open('./data/%s-git-log/%s.txt' % (upstream, forkPathName)) as f:
            lines = f.readlines()

        commit_ids = []
        currCommitIndex = -1
        newCommit = False
        modifiedFiles = []
        addedFiles = []
        deletedFiles = []
        commitsDetails = {}

        for i in range (0, len(lines)):
            line = lines[i]
            # get commit id
            if line.startswith("commit") and lines[i+1].startswith("Author"):
                newCommit = True
                splitStr = line.split()
                id = splitStr[1]
                #print(id)
                commit_ids.append(id)
                currCommitIndex += 1
            
            if line.startswith(':'):
                
                if newCommit:
                    # only do this when it's not the first commit 
                    if currCommitIndex > 0:
                        newCommit = False

                        # add info for fetched last commit_id to commitsDetails dictionary
                        commitID = commit_ids[currCommitIndex-1]
                        changed = {'M': modifiedFiles, 'A': addedFiles, 'D': deletedFiles}
                        commitsDetails[commitID] = changed

                        # clear the modified, added, deleted files lists
                        modifiedFiles = []
                        addedFiles = []
                        deletedFiles = []

                splitStr = line.split()
                fileChangeType = splitStr[4]
                fileName = splitStr[5]

                # if marked as 'M', add to modifiedFiles, 'A' for addedFiles, 
                # 'D' for deletedFile, else is renamed files 'R'
                if fileChangeType == 'M':
                    modifiedFiles.append(fileName)
                elif fileChangeType == 'A':
                    addedFiles.append(fileName)
                elif fileChangeType == 'D':
                    deletedFiles.append(fileName)
                else:
                    pass
                    #in the future, should do something to deal with the renamed files
                    #line content
                    #print("commit: " + commit_ids[currCommitIndex] + "\n" + line)

        # add info for fetched last commit_id to commitsDetails dictionary
        commitID = commit_ids[currCommitIndex]
        changed = {'M': modifiedFiles, 'A': addedFiles, 'D': deletedFiles}
        commitsDetails[commitID] = changed

        # save result as a txt file
        f = open("./data/%s-parsed/%s-parsed.txt" % (upstream, forkPathName),"w+")
        f.write(str(commitsDetails))
        f.close
    
    

    #create directory for summarized files
    upstream = repo_name.split('/')[0]
    if not os.path.isdir("./data/%s-summarized" % upstream):
        os.mkdir("./data/%s-summarized" % upstream)
    
    #summarize changed files
    totalModifiedDic = {}
    totalAddedDic = {}
    totalDeletedDic = {}

    totalModifiedForksDic = {}
    totalAddedForksDic = {}
    totalDeletedForksDic = {}

    totalModifiedShaDic = {}
    totalAddedShaDic = {}
    totalDeletedShaDic = {}


    for fork_name in forkNames:
        forkPathName = fork_name.split('/')[0]

        #if the txt file doesn't exist for the fork, skip
        if os.path.isfile('./data/%s-parsed/%s-parsed.txt' % (upstream, forkPathName)) == False:
            continue

        content = ""
        with open('./data/%s-parsed/%s-parsed.txt' % (upstream, forkPathName)) as f:
            content = f.read()

        commitsDetails = eval(content)

        modifiedDic = {}
        addedDic = {}
        deletedDic = {}

        modifiedShaDic = {}
        addedShaDic = {}
        deletedShaDic = {}

        for commitID in commitsDetails:
            changed = commitsDetails[commitID]
            if changed['M']:
                for item in changed['M']:
                    if item in modifiedDic:
                        modifiedDic[item] += 1

                    else:
                        modifiedDic[item] = 1
                        modifiedShaDic[item] = []
                    modifiedShaDic[item].append("https://api.github.com/repos/%s/openvpn/git/commits/%s" % (forkPathName, commitID))
                        
            if changed['A']:
                for item in changed['A']:
                    if item in addedDic:
                        addedDic[item] += 1
                    else:
                        addedDic[item] = 1
                        addedShaDic[item] = []
                    addedShaDic[item].append("https://api.github.com/repos/%s/openvpn/git/commits/%s" % (forkPathName, commitID))
            
            if changed['D']:
                for item in changed['D']:
                    if item in deletedDic:
                        deletedDic[item] += 1
                    else:
                        deletedDic[item] = 1
                        deletedShaDic[item] = []
                    deletedShaDic[item].append("https://api.github.com/repos/%s/openvpn/git/commits/%s" % (forkPathName, commitID))

        sortedModifiedList = sorted(modifiedDic.items(), key=lambda x: x[1], reverse=True)
        sortedAddedList = sorted(addedDic.items(), key=lambda x: x[1], reverse=True)
        sortedDeletedList = sorted(deletedDic.items(), key=lambda x: x[1], reverse=True)

        # save result as a txt file
        f = open("./data/%s-summarized/%s.txt" % (upstream, forkPathName),"w+")
        f.writelines(["sortedModifiedList: \n", str(sortedModifiedList), "\n\n", "sortedAddedList: \n", str(sortedAddedList), "\n\n", "sortedDeletedList: \n", str(sortedDeletedList)])
        f.close

        #add to total changed files count
        for item in modifiedDic:
            if item in totalModifiedForksDic:
                totalModifiedDic[item] += modifiedDic[item]
            else:
                totalModifiedDic[item] = modifiedDic[item]
                totalModifiedForksDic[item] = []
                totalModifiedShaDic[item] = []
            totalModifiedForksDic[item].append(fork_name)
            for shaLink in modifiedShaDic[item]:
                totalModifiedShaDic[item].append(shaLink)

        for item in addedDic:
            if item in totalAddedForksDic:
                totalAddedDic[item] += addedDic[item]
            else:
                totalAddedDic[item] = addedDic[item]
                totalAddedForksDic[item] = []
                totalAddedShaDic[item] = []
            totalAddedForksDic[item].append(fork_name)
            for shaLink in addedShaDic[item]:
                totalAddedShaDic[item].append(shaLink)

        for item in deletedDic:
            if item in totalDeletedForksDic:
                totalDeletedDic[item] += deletedDic[item]
            else:
                totalDeletedDic[item] = deletedDic[item]
                totalDeletedForksDic[item] = []
                totalDeletedShaDic[item] = []
            totalDeletedForksDic[item].append(fork_name)
            for shaLink in deletedShaDic[item]:
                totalDeletedShaDic[item].append(shaLink)
            

    #sort total changed files count
    sortedTotalModifiedList = sorted(totalModifiedDic.items(), key=lambda x: x[1], reverse=True)
    sortedTotalAddedList = sorted(totalAddedDic.items(), key=lambda x: x[1], reverse=True)
    sortedTotalDeletedList = sorted(totalDeletedDic.items(), key=lambda x: x[1], reverse=True)

    #save result in a csv file 
    workbook = openpyxl.Workbook()

    wsMod = workbook.active
    wsMod.title = 'Modified'
    wsAdd = workbook.create_sheet('Added')
    wsDel = workbook.create_sheet('Deleted')

    # write to modified
    # titles
    wsMod['A1'] = 'File Name'
    wsMod['B1'] = 'Number of Changes at Commit Level'
    wsMod['C1'] = 'List of Forks'
    wsMod['D1'] = 'List of Sha links'

    for i in range(0, len(sortedTotalModifiedList)):
        fileName = sortedTotalModifiedList[i][0]
        wsMod.cell(row=i+2, column=1).value = fileName
        wsMod.cell(row=i+2, column=2).value = sortedTotalModifiedList[i][1]
        wsMod.cell(row=i+2, column=3).value = str(totalModifiedForksDic[fileName])
        wsMod.cell(row=i+2, column=4).value = str(totalModifiedShaDic[fileName])

    # write to added
    # titles
    wsAdd['A1'] = 'File Name'
    wsAdd['B1'] = 'Number of Changes at Commit Level'
    wsAdd['C1'] = 'List of Forks'
    wsAdd['D1'] = 'List of Sha links'

    for i in range(0, len(sortedTotalAddedList)):
        fileName = sortedTotalAddedList[i][0]
        wsAdd.cell(row=i+2, column=1).value = fileName
        wsAdd.cell(row=i+2, column=2).value = sortedTotalAddedList[i][1]
        wsAdd.cell(row=i+2, column=3).value = str(totalAddedForksDic[fileName])
        wsAdd.cell(row=i+2, column=4).value = str(totalAddedShaDic[fileName])

    # write to deleted
    # titles
    wsDel['A1'] = 'File Name'
    wsDel['B1'] = 'Number of Changes at Commit Level'
    wsDel['C1'] = 'List of Forks'
    wsDel['D1'] = 'List of Sha links'

    for i in range(0, len(sortedTotalDeletedList)):
        fileName = sortedTotalDeletedList[i][0]
        wsDel.cell(row=i+2, column=1).value = fileName
        wsDel.cell(row=i+2, column=2).value = sortedTotalDeletedList[i][1]
        wsDel.cell(row=i+2, column=3).value = str(totalDeletedForksDic[fileName])
        wsDel.cell(row=i+2, column=4).value = str(totalDeletedShaDic[fileName])

    workbook.save('./data/%s-result.xlsx' % upstream)


    
    # create directory for generated images
    if not os.path.isdir("./data/images"):
        os.mkdir("./data/images")

    # visualize changed files

    # modified visual
    count = 0
    topTenFilenames = []
    topTenStat = []
    while count < 10 and count < len(sortedTotalModifiedList):
        topTenFilenames.append(sortedTotalModifiedList[count][0])
        topTenStat.append(sortedTotalModifiedList[count][1])
        count += 1
    
    if topTenFilenames:
        fig = plt.figure()

        # plot bar graph
        plt.barh(topTenFilenames, topTenStat)

        # fit the names on x-axis
        #fig.autofmt_xdate()

        # set titles
        plt.title('Top 10 Modified Files Hotspots')
        plt.ylabel('File Names')
        plt.xlabel('Number of Commits')
        plt.gca().invert_yaxis()
        plt.tight_layout()
        
        # save figure
        plt.savefig('./data/images/modified.png')
        


    # added visual
    count = 0
    topTenFilenames = []
    topTenStat = []
    while count < 10 and count < len(sortedTotalAddedList):
        topTenFilenames.append(sortedTotalAddedList[count][0])
        topTenStat.append(sortedTotalAddedList[count][1])
        count += 1

    if topTenFilenames:
        fig = plt.figure()

        # plot bar graph
        plt.barh(topTenFilenames, topTenStat)

        # fit the names on x-axis
        #fig.autofmt_xdate()

        # set titles
        plt.title('Top 10 Added Files Hotspots')
        plt.ylabel('File Names')
        plt.xlabel('Number of Commits')
        plt.gca().invert_yaxis()
        plt.tight_layout()
        
        # save figure
        plt.savefig('./data/images/added.png')
        

    # deleted visual
    count = 0
    topTenFilenames = []
    topTenStat = []
    while count < 10 and count < len(sortedTotalDeletedList):
        topTenFilenames.append(sortedTotalDeletedList[count][0])
        topTenStat.append(sortedTotalDeletedList[count][1])
        count += 1

    if topTenFilenames:
        fig = plt.figure()

        # plot bar graph
        plt.barh(topTenFilenames, topTenStat)

        # fit the names on x-axis
        #fig.autofmt_xdate()

        # set titles
        plt.title('Top 10 Deleted Files Hotspots')
        plt.ylabel('File Names')
        plt.xlabel('Number of Commits')
        plt.gca().invert_yaxis()
        plt.tight_layout()
        
        # save figure
        plt.savefig('./data/images/deleted.png')
    

    #delete all cloned repos (uncomment the line when needs to remove all the cloned repo)
    #rmtree('./cloned')

    


